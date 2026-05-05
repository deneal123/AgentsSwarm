from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from service.infrastructure.messaging import stream_helpers

logger = logging.getLogger(__name__)


class AnalyticsVitalsRepository:
    def __init__(self, redis_client: Any | None, stream_name: str = "analytics:vitals") -> None:
        self._redis_client = redis_client
        self._stream_name = stream_name

    async def persist_batch(self, payload: dict[str, Any]) -> None:
        if not self._redis_client:
            return

        ts = datetime.now(timezone.utc).isoformat()
        await stream_helpers.xadd(
            self._redis_client,
            self._stream_name,
            {
                "data": json.dumps(payload, ensure_ascii=False),
                "ts": ts,
            },
        )

        for event in payload.get("events", []):
            await self._update_metric_aggregate(event, ts)

    async def _update_metric_aggregate(self, event: dict[str, Any], timestamp: str) -> None:
        if not self._redis_client:
            return

        metric_name = str(event.get("name", "unknown")).upper()
        rating = str(event.get("rating", "unknown"))
        value = float(event.get("value", 0))

        key = f"analytics:vitals:agg:{metric_name}"
        history_key = f"analytics:vitals:values:{metric_name}"

        await self._run_redis("hincrby", key, "count", 1)
        await self._run_redis("hincrbyfloat", key, "sum", value)
        await self._run_redis("hset", key, "updated_at", timestamp)
        await self._run_redis("hincrby", key, f"rating:{rating}", 1)
        await self._run_redis("zadd", history_key, {f"{timestamp}:{value}": value})
        await self._run_redis("zremrangebyrank", history_key, 0, -2001)

    async def fetch_summary(self) -> dict[str, Any]:
        if not self._redis_client:
            return {"updated_at": datetime.now(timezone.utc), "total_events": 0, "metrics": []}

        metrics: list[dict[str, Any]] = []
        total_events = 0
        latest_update: datetime | None = None

        for metric_name in ("CLS", "FCP", "FID", "INP", "LCP", "TTFB"):
            key = f"analytics:vitals:agg:{metric_name}"
            history_key = f"analytics:vitals:values:{metric_name}"
            raw = await self._run_redis("hgetall", key)
            if not raw:
                continue

            normalized = self._normalize_hash(raw)
            count = int(float(normalized.get("count", 0)))
            if count <= 0:
                continue

            sum_value = float(normalized.get("sum", 0))
            good = int(float(normalized.get("rating:good", 0)))
            needs = int(float(normalized.get("rating:needs-improvement", 0)))
            poor = int(float(normalized.get("rating:poor", 0)))
            updated_at = datetime.fromisoformat(normalized.get("updated_at")) if normalized.get("updated_at") else datetime.now(timezone.utc)

            if latest_update is None or updated_at > latest_update:
                latest_update = updated_at

            p95 = await self._compute_p95(history_key)
            total_events += count
            metrics.append(
                {
                    "name": metric_name,
                    "count": count,
                    "avg": round(sum_value / count, 4),
                    "p95": round(p95, 4),
                    "good_rate": round(good / count if count else 0, 4),
                    "needs_improvement_rate": round(needs / count if count else 0, 4),
                    "poor_rate": round(poor / count if count else 0, 4),
                }
            )

        return {
            "updated_at": latest_update or datetime.now(timezone.utc),
            "total_events": total_events,
            "metrics": metrics,
        }

    async def _compute_p95(self, history_key: str) -> float:
        values_raw = await self._run_redis("zrange", history_key, 0, -1, withscores=True)
        if not values_raw:
            return 0.0

        scores = sorted(float(item[1]) for item in values_raw)
        index = max(0, min(len(scores) - 1, int(len(scores) * 0.95) - 1))
        return scores[index]

    async def _run_redis(self, method_name: str, *args, **kwargs):
        method = getattr(self._redis_client, method_name, None)
        if not callable(method):
            return None
        result = method(*args, **kwargs)
        if hasattr(result, "__await__"):
            return await result
        return result

    @staticmethod
    def _normalize_hash(raw: dict[Any, Any]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for key, value in raw.items():
            parsed_key = key.decode() if isinstance(key, bytes) else str(key)
            parsed_value = value.decode() if isinstance(value, bytes) else str(value)
            normalized[parsed_key] = parsed_value
        return normalized

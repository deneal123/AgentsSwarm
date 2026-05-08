import asyncio
import json
import logging
from datetime import datetime

from service.infrastructure.messaging import stream_helpers
from service.services.chat.presentation.ws.chat_ws.metrics import ChatWsMetrics

logger = logging.getLogger(__name__)


class ChatStreamConsumer:
    def __init__(self, redis_client, settings, metrics: ChatWsMetrics) -> None:
        self._redis_client = redis_client
        self._settings = settings
        self._metrics = metrics

    async def ensure_group(self, stream_key: str, group: str) -> None:
        await stream_helpers.ensure_group(self._redis_client, stream_key, group, mkstream=True)

    async def handle_replay(self, websocket, stream_key: str, last_id: str) -> None:
        replay_count = min(self._settings.max_replay, 100)
        entries = await stream_helpers.xrange(self._redis_client, stream_key, last_id, "+", count=replay_count)
        for entry_id, fields in entries:
            payload = self.parse_payload(fields)
            await websocket.send_json({"type": "replay", "id": entry_id, "data": payload})
            self._metrics.inc("replay_sent_total")

    async def process_claimed_entries(self, websocket, stream_key: str, group: str, claimed: list) -> None:
        for entry_id, fields in claimed:
            payload = self.parse_payload(fields)
            try:
                await websocket.send_json({"type": "claimed", "id": entry_id, "data": payload})
                self._metrics.inc("claimed_sent_total")
            except Exception:
                self._metrics.inc("claimed_left_unacked_total")
                logger.debug("Failed sending claimed entry %s", entry_id, exc_info=True)
                continue

            try:
                await stream_helpers.xack(self._redis_client, stream_key, group, entry_id)
            except Exception:
                self._metrics.inc("xack_errors_total")
                logger.debug("Failed xack for claimed entry %s", entry_id, exc_info=True)

    async def handle_pending_messages(self, websocket, stream_key: str, group: str, consumer: str) -> None:
        pending = await stream_helpers.xpending(self._redis_client, stream_key, group)
        pending_count = pending.get("count", 0) if pending else 0
        if pending_count <= 0:
            return

        claim_limit = min(pending_count, self._settings.max_claim)
        claimed = await stream_helpers.xauto_claim(
            self._redis_client,
            stream_key,
            group,
            consumer,
            min_idle_ms=self._settings.pel_min_idle_ms,
            count=claim_limit,
        )
        await self.process_claimed_entries(websocket, stream_key, group, claimed)

    async def consume_events(self, websocket, stream_key: str, group: str, consumer: str, start_from_latest: bool = False) -> None:
        last_id = "$" if start_from_latest else "0"
        while True:
            try:
                messages = await stream_helpers.xread(
                    self._redis_client,
                    streams={stream_key: last_id},
                    count=10,
                    block=1000,
                )
                for _, message_list in messages:
                    for message_id, fields in message_list:
                        event_data = self.parse_payload(fields)
                        payload = self.build_event_payload(event_data)
                        await websocket.send_json(payload)
                        self._metrics.inc("events_sent_total")
                        last_id = message_id
            except Exception as exc:
                logger.exception("Error reading from Redis stream: %s", exc)
                await asyncio.sleep(1)
            await asyncio.sleep(0.1)

    @staticmethod
    def parse_payload(fields: dict) -> dict:
        try:
            data = fields.get("data") if isinstance(fields, dict) else fields
            return json.loads(data) if isinstance(data, str) else (data or {})
        except Exception:
            return {}

    @staticmethod
    def build_event_payload(event_data: dict) -> dict:
        event_type = event_data.get("type") or event_data.get("event")
        timestamp = event_data.get("timestamp") or datetime.now().isoformat()
        if event_type == "agent_reply":
            return {
                "type": "agent_reply",
                "job_id": event_data.get("job_id"),
                "reply": event_data.get("reply"),
                "file_url": event_data.get("file_url"),
                "error": event_data.get("error"),
                "metadata": event_data.get("metadata"),
                "timestamp": timestamp,
            }
        if event_type == "stream_chunk":
            return {
                "type": "stream_chunk",
                "data": event_data.get("data"),
                "job_id": event_data.get("job_id"),
                "metadata": event_data.get("metadata"),
                "seq": event_data.get("seq"),
                "timestamp": timestamp,
            }
        return {
            "type": event_type,
            "job_id": event_data.get("job_id"),
            "data": event_data.get("data", event_data),
            "metadata": event_data.get("metadata"),
            "seq": event_data.get("seq"),
            "timestamp": timestamp,
        }

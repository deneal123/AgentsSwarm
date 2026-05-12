from fastapi.testclient import TestClient

from service.main import app
from service.composition.state import get_analytics_service
from service.services.analytics.persistence.analytics_repository import AnalyticsVitalsRepository
from service.services.analytics.application.analytics_service import AnalyticsService


class FakeRedis:
    def __init__(self):
        self.hashes = {
            "analytics:vitals:agg:LCP": {
                "count": "10",
                "sum": "25000",
                "rating:good": "7",
                "rating:needs-improvement": "2",
                "rating:poor": "1",
                "updated_at": "2026-04-23T00:00:00+00:00",
            }
        }
        self.sorted = {
            "analytics:vitals:values:LCP": [
                ("1", 1000.0),
                ("2", 1200.0),
                ("3", 1600.0),
                ("4", 1900.0),
                ("5", 2000.0),
                ("6", 2100.0),
                ("7", 2300.0),
                ("8", 2600.0),
                ("9", 2900.0),
                ("10", 3400.0),
            ]
        }

    def hgetall(self, key):
        return self.hashes.get(key, {})

    def zrange(self, key, start, end, withscores=False):
        if withscores:
            return self.sorted.get(key, [])
        return []


class _FakeAnalyticsService:
    async def ingest_vitals(self, payload: dict) -> int:
        return len(payload.get("events", []))

    async def fetch_summary(self) -> dict:
        return {"total_events": 0, "metrics": []}


def test_ingest_vitals_accepts_payload():
    app.dependency_overrides[get_analytics_service] = lambda: _FakeAnalyticsService()
    try:
        client = TestClient(app)
        response = client.post(
            "/api/analytics/vitals",
            json={
                "version": "1.0",
                "sampled": True,
                "events": [
                    {"name": "LCP", "value": 1234, "rating": "good"},
                    {"name": "CLS", "value": 0.03, "rating": "good"},
                ],
            },
        )

        assert response.status_code == 200
        assert response.json() == {"accepted": True, "enqueued": 2}
    finally:
        app.dependency_overrides.pop(get_analytics_service, None)


def test_vitals_summary_returns_aggregates():
    client = TestClient(app)
    fake_redis = FakeRedis()

    def override_service():
        return AnalyticsService(AnalyticsVitalsRepository(fake_redis))

    app.dependency_overrides[get_analytics_service] = override_service

    try:
        response = client.get("/api/analytics/vitals/summary")

        assert response.status_code == 200
        body = response.json()
        assert body["total_events"] == 10
        assert len(body["metrics"]) == 1
        assert body["metrics"][0]["name"] == "LCP"
        assert body["metrics"][0]["avg"] == 2500.0
    finally:
        app.dependency_overrides.pop(get_analytics_service, None)

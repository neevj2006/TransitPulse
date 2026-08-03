from httpx import ASGITransport, AsyncClient

from transitpulse.app import create_app
from transitpulse.config import Settings


async def test_reliability_returns_safe_unavailable_problem_without_database() -> None:
    app = create_app(Settings(environment="test", database_url=None, redis_url=None), probes=[])
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/reliability")
    assert response.status_code == 503
    assert response.json()["code"] == "HISTORY_UNAVAILABLE"


async def test_transfer_risk_returns_safe_unavailable_problem_without_database() -> None:
    app = create_app(Settings(environment="test", database_url=None, redis_url=None), probes=[])
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/transfer-risk?arriving_route_id=Red&arriving_stop_id=Harvard"
            "&connecting_route_id=Orange&connecting_stop_id=Downtown&planned_arrival=2026-08-01T10:00:00Z"
            "&planned_departure=2026-08-01T10:10:00Z"
        )
    assert response.status_code == 503
    assert response.json()["code"] == "HISTORY_UNAVAILABLE"

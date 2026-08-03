from datetime import UTC, datetime

from httpx import ASGITransport, AsyncClient

from transitpulse.app import create_app
from transitpulse.config import Settings


class _FixtureResult:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows

    def mappings(self) -> "_FixtureResult":
        return self

    def all(self) -> list[dict[str, object]]:
        return self.rows


class _ChronologicalFixtureEngine:
    def connect(self) -> "_ChronologicalFixtureEngine":
        return self

    async def __aenter__(self) -> "_ChronologicalFixtureEngine":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def execute(self, query: object, parameters: dict[str, object]) -> _FixtureResult:
        assert parameters["cutoff"] == datetime(2026, 8, 1, 10, tzinfo=UTC)
        delay_column = "arrival" if "arrival_delay_seconds" in str(query) else "departure"
        return _FixtureResult(
            [{"delay": 0, "observed_at": datetime(2026, 7, 31, 10, tzinfo=UTC)} for _ in range(20)]
            if delay_column in {"arrival", "departure"}
            else []
        )


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


async def test_transfer_risk_uses_the_planned_journey_as_a_chronological_cutoff() -> None:
    app = create_app(Settings(environment="test", database_url=None, redis_url=None), probes=[])
    app.state.schedule_engine = _ChronologicalFixtureEngine()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/transfer-risk?arriving_route_id=Red&arriving_stop_id=Harvard"
            "&connecting_route_id=Orange&connecting_stop_id=Downtown&planned_arrival=2026-08-01T10:00:00Z"
            "&planned_departure=2026-08-01T10:10:00Z"
        )
    assert response.status_code == 200
    assert response.json()["data"]["missed_transfer_probability"] == 0

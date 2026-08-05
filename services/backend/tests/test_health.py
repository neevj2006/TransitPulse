from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from transitpulse.app import create_app
from transitpulse.config import Settings


class HealthyProbe:
    name = "dependency"

    async def check(self) -> None:
        return None

    async def close(self) -> None:
        return None


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = create_app(
        Settings(environment="test", database_url=None, redis_url=None),
        probes=[HealthyProbe()],
    )
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as test_client:
            yield test_client


async def test_liveness(client: AsyncClient) -> None:
    response = await client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {
        "service": "transitpulse-backend",
        "status": "live",
    }


async def test_metrics_exposes_request_measurements(client: AsyncClient) -> None:
    await client.get("/health/live")
    response = await client.get("/metrics")

    assert response.status_code == 200
    assert "transitpulse_http_requests_total" in response.text


async def test_rate_limit_client_state_is_bounded(client: AsyncClient) -> None:
    client._transport.app.state.request_windows = {str(index): [] for index in range(10_000)}  # type: ignore[attr-defined]

    response = await client.get("/health/live")

    assert response.status_code == 200
    assert len(client._transport.app.state.request_windows) == 10_000  # type: ignore[attr-defined]


async def test_cors_is_narrow_by_default(client: AsyncClient) -> None:
    response = await client.options(
        "/api/v1/live/health",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
    )
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


async def test_live_health_has_versioned_poll_history_metadata(client: AsyncClient) -> None:
    response = await client.get("/api/v1/live/health")

    assert response.status_code == 200
    assert response.json()["schema_version"] == "1.0.0"
    assert response.json()["meta"]["recent_polls"] == []
    assert response.json()["meta"]["diagnostics"] == []


async def test_live_health_exposes_safe_entity_and_quality_summaries() -> None:
    class Cache:
        async def source_health(self, source_id: str) -> dict[str, object]:
            return {
                "source_id": source_id,
                "diagnostics": {
                    "accepted": 8,
                    "unreconciled": 2,
                    "parser_errors": 1,
                    "duplicates": 3,
                    "reconciliation_partial": 2,
                },
            }

        async def telemetry(self) -> dict[str, int]:
            return {"key_count": 4, "memory_bytes": 512, "evicted_keys": 0}

    app = create_app(Settings(environment="test", redis_url=None), probes=[])
    app.state.redis_state_store = Cache()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        response = await test_client.get("/api/v1/live/health")

    assert response.status_code == 200
    source = response.json()["data"][0]
    assert source["entity_counts"] == {"accepted": 8}
    assert source["rejection_counts"]["unreconciled"] == 2
    assert source["diagnostic_rates"]["parser_failure_rate"] == 0.1
    assert source["diagnostic_scope"] == "TRANSITPULSE_INFERENCE"
    assert response.json()["meta"]["cache_telemetry"]["memory_bytes"] == 512


async def test_invalid_requests_use_a_safe_consistent_problem_shape(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/routes", params={"limit": 0}, headers={"X-Request-ID": "test"}
    )
    assert response.status_code == 422
    assert response.json() == {
        "code": "INVALID_REQUEST",
        "message": "One or more request parameters are invalid.",
        "request_id": "test",
    }


async def test_readiness_checks_dependencies(client: AsyncClient) -> None:
    response = await client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {
        "checks": {"dependency": "ready"},
        "status": "ready",
    }


async def test_version(client: AsyncClient) -> None:
    response = await client.get("/version")
    assert response.status_code == 200
    assert response.json() == {
        "environment": "test",
        "service": "transitpulse-backend",
        "version": "0.1.0",
    }


async def test_readiness_requires_configured_dependencies() -> None:
    app = create_app(Settings(environment="test"), probes=[])
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"checks": {}, "status": "not_ready"}

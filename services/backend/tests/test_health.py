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
    app = create_app(Settings(environment="test"), probes=[HealthyProbe()])
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

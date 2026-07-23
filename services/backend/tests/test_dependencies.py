import os

import pytest
from httpx import ASGITransport, AsyncClient

from transitpulse.app import create_app
from transitpulse.config import Settings


@pytest.mark.integration
async def test_configured_dependencies_are_ready() -> None:
    if not os.getenv("TP_DATABASE_URL") or not os.getenv("TP_REDIS_URL"):
        pytest.skip("PostgreSQL and Valkey URLs are not configured")

    app = create_app(Settings())
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "checks": {"postgresql": "ready", "valkey": "ready"},
        "status": "ready",
    }

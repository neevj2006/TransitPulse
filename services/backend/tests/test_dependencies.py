import os
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from transitpulse.app import create_app
from transitpulse.config import Settings
from transitpulse.schedule.models import Route, Schedule, Trip
from transitpulse.schedule.persistence import persist_and_activate


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


@pytest.mark.integration
async def test_static_feed_version_activation_persists_provenance() -> None:
    database_url = os.getenv("TP_DATABASE_URL")
    if not database_url:
        pytest.skip("PostgreSQL URL is not configured")
    engine = create_async_engine(database_url)
    async with engine.connect() as connection:
        previous = await connection.execute(
            text(
                "SELECT feed_version_id FROM static_feed_versions "
                "WHERE import_status = 'ACTIVE' LIMIT 1"
            )
        )
        previous_version_id = previous.scalar_one_or_none()
    schedule = Schedule(version="integration", checksum=uuid4().hex)
    version_id = await persist_and_activate(
        engine,
        schedule,
        source_url="https://example.test/gtfs.zip",
    )
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text(
                    "SELECT import_status, source_url, feed_label "
                    "FROM static_feed_versions WHERE feed_version_id = :id"
                ),
                {"id": version_id},
            )
        assert result.one() == ("ACTIVE", "https://example.test/gtfs.zip", "integration")
    finally:
        async with engine.begin() as connection:
            await connection.execute(
                text("DELETE FROM static_feed_versions WHERE feed_version_id = :id"),
                {"id": version_id},
            )
            if previous_version_id:
                await connection.execute(
                    text(
                        "UPDATE static_feed_versions SET import_status = 'ACTIVE' "
                        "WHERE feed_version_id = :id"
                    ),
                    {"id": previous_version_id},
                )
        await engine.dispose()


@pytest.mark.integration
async def test_failed_static_import_rolls_back_the_pending_feed_version() -> None:
    database_url = os.getenv("TP_DATABASE_URL")
    if not database_url:
        pytest.skip("PostgreSQL URL is not configured")
    engine = create_async_engine(database_url)
    checksum = uuid4().hex
    invalid = Schedule(
        version="rollback-test",
        checksum=checksum,
        routes={"route": Route("route", "R", None, 3)},
        trips={"trip": Trip("trip", "route", "missing-service", None, None)},
    )
    with pytest.raises(IntegrityError):
        await persist_and_activate(engine, invalid)
    async with engine.connect() as connection:
        result = await connection.execute(
            text("SELECT count(*) FROM static_feed_versions WHERE payload_checksum = :checksum"),
            {"checksum": checksum},
        )
    await engine.dispose()
    assert result.scalar_one() == 0

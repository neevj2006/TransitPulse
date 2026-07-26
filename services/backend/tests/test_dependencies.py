import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from transitpulse.app import create_app
from transitpulse.cache import RedisStateStore
from transitpulse.config import Settings
from transitpulse.history import RealtimeHistoryStore
from transitpulse.polling import PollResult
from transitpulse.realtime import StopPrediction, TripUpdate, Vehicle
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


@pytest.mark.integration
async def test_realtime_history_and_operational_usage_are_measurable() -> None:
    database_url = os.getenv("TP_DATABASE_URL")
    redis_url = os.getenv("TP_REDIS_URL")
    if not database_url or not redis_url:
        pytest.skip("PostgreSQL and Valkey URLs are not configured")
    engine = create_async_engine(database_url)
    history = RealtimeHistoryStore(engine)
    now = datetime.now(UTC)
    unique = uuid4().hex
    source_id = f"integration-{unique}"
    trip_id = f"trip-{unique}"
    await history.record_poll(
        PollResult(source_id, now, now, "ERROR", 503, None, 0, "SOURCE_HTTP_ERROR")
    )
    await history.record_trip_updates(
        [
            TripUpdate(
                unique,
                trip_id,
                "Red",
                None,
                now,
                "3",
                (
                    StopPrediction(
                        "stop",
                        1,
                        now + timedelta(minutes=2),
                        None,
                        "1",
                        90,
                        None,
                    ),
                ),
            )
        ],
        now,
    )
    await history.record_quality(
        source_id,
        "vehicle",
        unique,
        "Red",
        "VEHICLE_FROZEN",
        now,
        "MATCHED",
        "HIGH",
    )
    usage = await history.measure_usage()
    async with engine.begin() as connection:
        quality = await connection.execute(
            text(
                "SELECT signal FROM realtime_quality_events "
                "WHERE source_id = :source ORDER BY signal"
            ),
            {"source": source_id},
        )
        trip = await connection.execute(
            text(
                "SELECT trip_relationship, stop_relationship, arrival_delay_seconds "
                "FROM trip_update_observations WHERE trip_id = :trip"
            ),
            {"trip": trip_id},
        )
    removed = await history.prune_observations(now + timedelta(minutes=1))
    async with engine.begin() as connection:
        await connection.execute(
            text("DELETE FROM realtime_quality_events WHERE source_id = :source"),
            {"source": source_id},
        )
        await connection.execute(
            text("DELETE FROM trip_update_observations WHERE trip_id = :trip"),
            {"trip": trip_id},
        )
        await connection.execute(
            text("DELETE FROM feed_polls WHERE source_id = :source"),
            {"source": source_id},
        )
    assert [row.signal for row in quality] == ["FEED_GAP", "VEHICLE_FROZEN"]
    assert trip.one() == ("3", "1", 90)
    assert removed >= 3
    assert isinstance(usage["observations"], int)
    assert isinstance(usage["storage_bytes"], int)
    assert usage["observations"] >= 1
    assert usage["storage_bytes"] > 0
    await engine.dispose()

    client: Redis = Redis.from_url(  # pyright: ignore[reportUnknownMemberType]
        redis_url, decode_responses=True
    )
    cache = RedisStateStore(client)
    vehicle_id = f"vehicle-{unique}"
    await cache.put_vehicle(Vehicle(unique, vehicle_id, "Red", trip_id, 42, -71, now))
    await cache.route_vehicles("Red")
    telemetry = await cache.telemetry()
    await client.delete(
        f"tp:v1:{{mbta}}:vehicle:{vehicle_id}",
        "tp:v1:{mbta}:route:Red:vehicles",
    )
    await cache.close()
    assert isinstance(telemetry["key_count"], int)
    assert isinstance(telemetry["memory_bytes"], int)
    assert isinstance(telemetry["commands_processed"], int)
    assert telemetry["key_count"] >= 1
    assert telemetry["memory_bytes"] > 0
    assert telemetry["commands_processed"] > 0
    assert telemetry["hit_rate_percent"] is not None

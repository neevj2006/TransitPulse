# ruff: noqa: E501
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from transitpulse.schedule.models import Schedule


async def persist_and_activate(
    engine: AsyncEngine, schedule: Schedule, agency_id: str = "mbta"
) -> str:
    """Persist a fully parsed schedule in one transaction, then atomically activate it."""
    version_id = str(uuid4())
    async with engine.begin() as connection:
        existing = await connection.execute(
            text(
                "SELECT feed_version_id FROM static_feed_versions WHERE agency_id = :agency AND payload_checksum = :checksum"
            ),
            {"agency": agency_id, "checksum": schedule.checksum},
        )
        row = existing.first()
        if row:
            return str(row[0])
        await connection.execute(
            text(
                "INSERT INTO static_feed_versions (feed_version_id, agency_id, payload_checksum, retrieved_at, import_status) VALUES (:id, :agency, :checksum, :retrieved, 'PENDING')"
            ),
            {
                "id": version_id,
                "agency": agency_id,
                "checksum": schedule.checksum,
                "retrieved": datetime.now(UTC),
            },
        )
        for route in schedule.routes.values():
            await connection.execute(
                text(
                    "INSERT INTO routes (feed_version_id, route_id, short_name, long_name, route_type, source_color) VALUES (:version, :id, :short, :long, :type, :color)"
                ),
                {
                    "version": version_id,
                    "id": route.route_id,
                    "short": route.short_name,
                    "long": route.long_name,
                    "type": route.route_type,
                    "color": route.color,
                },
            )
        for stop in schedule.stops.values():
            await connection.execute(
                text(
                    "INSERT INTO stops (feed_version_id, stop_id, name, latitude, longitude, position) VALUES (:version, :id, :name, :lat, :lon, CASE WHEN :lat IS NULL THEN NULL ELSE ST_SetSRID(ST_MakePoint(:lon, :lat), 4326) END)"
                ),
                {
                    "version": version_id,
                    "id": stop.stop_id,
                    "name": stop.name,
                    "lat": stop.latitude,
                    "lon": stop.longitude,
                },
            )
        await connection.execute(
            text(
                "UPDATE static_feed_versions SET import_status = 'SUPERSEDED' WHERE agency_id = :agency AND import_status = 'ACTIVE'"
            ),
            {"agency": agency_id},
        )
        await connection.execute(
            text(
                "UPDATE static_feed_versions SET import_status = 'ACTIVE' WHERE feed_version_id = :id"
            ),
            {"id": version_id},
        )
    return version_id

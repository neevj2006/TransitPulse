# ruff: noqa: E501
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from transitpulse.schedule.models import Schedule


async def persist_and_activate(
    engine: AsyncEngine,
    schedule: Schedule,
    agency_id: str = "mbta",
    source_url: str | None = None,
    retrieved_at: datetime | None = None,
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
                "INSERT INTO static_feed_versions (feed_version_id, agency_id, payload_checksum, retrieved_at, source_url, feed_label, import_status) VALUES (:id, :agency, :checksum, :retrieved, :source_url, :feed_label, 'PENDING')"
            ),
            {
                "id": version_id,
                "agency": agency_id,
                "checksum": schedule.checksum,
                "retrieved": retrieved_at or datetime.now(UTC),
                "source_url": source_url,
                "feed_label": schedule.version,
            },
        )
        for agency in schedule.agencies.values():
            await connection.execute(
                text(
                    "INSERT INTO agencies (feed_version_id, agency_id, name, timezone) VALUES (:version, :id, :name, :timezone)"
                ),
                {
                    "version": version_id,
                    "id": agency.agency_id,
                    "name": agency.name,
                    "timezone": agency.timezone,
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
        for service in schedule.services.values():
            await connection.execute(
                text(
                    "INSERT INTO services (feed_version_id, service_id, monday, tuesday, wednesday, thursday, friday, saturday, sunday, start_date, end_date) VALUES (:version, :id, :monday, :tuesday, :wednesday, :thursday, :friday, :saturday, :sunday, :start, :end)"
                ),
                {
                    "version": version_id,
                    "id": service.service_id,
                    "monday": service.weekdays[0],
                    "tuesday": service.weekdays[1],
                    "wednesday": service.weekdays[2],
                    "thursday": service.weekdays[3],
                    "friday": service.weekdays[4],
                    "saturday": service.weekdays[5],
                    "sunday": service.weekdays[6],
                    "start": service.start_date,
                    "end": service.end_date,
                },
            )
        for trip in schedule.trips.values():
            await connection.execute(
                text(
                    "INSERT INTO trips (feed_version_id, trip_id, route_id, service_id, shape_id, headsign) VALUES (:version, :id, :route, :service, :shape, :headsign)"
                ),
                {
                    "version": version_id,
                    "id": trip.trip_id,
                    "route": trip.route_id,
                    "service": trip.service_id,
                    "shape": trip.shape_id,
                    "headsign": trip.headsign,
                },
            )
        for (service_id, service_date), is_added in schedule.exceptions.items():
            await connection.execute(
                text(
                    "INSERT INTO service_exceptions (feed_version_id, service_id, service_date, is_added) VALUES (:version, :service, :date, :added)"
                ),
                {
                    "version": version_id,
                    "service": service_id,
                    "date": service_date,
                    "added": is_added,
                },
            )
        for stop_time in schedule.stop_times:
            await connection.execute(
                text(
                    "INSERT INTO stop_times (feed_version_id, trip_id, stop_sequence, stop_id, arrival_seconds, departure_seconds) VALUES (:version, :trip, :sequence, :stop, :arrival, :departure)"
                ),
                {
                    "version": version_id,
                    "trip": stop_time.trip_id,
                    "sequence": stop_time.sequence,
                    "stop": stop_time.stop_id,
                    "arrival": stop_time.arrival_seconds,
                    "departure": stop_time.departure_seconds,
                },
            )
        for shape_id, points in schedule.shapes.items():
            for sequence, latitude, longitude in points:
                await connection.execute(
                    text(
                        "INSERT INTO shape_points (feed_version_id, shape_id, sequence, latitude, longitude) VALUES (:version, :shape, :sequence, :lat, :lon)"
                    ),
                    {
                        "version": version_id,
                        "shape": shape_id,
                        "sequence": sequence,
                        "lat": latitude,
                        "lon": longitude,
                    },
                )
        for transfer in schedule.transfers:
            await connection.execute(
                text(
                    "INSERT INTO transfers (feed_version_id, from_stop_id, to_stop_id, transfer_type, minimum_transfer_seconds) VALUES (:version, :from_stop, :to_stop, :type, :minimum)"
                ),
                {
                    "version": version_id,
                    "from_stop": transfer.from_stop_id,
                    "to_stop": transfer.to_stop_id,
                    "type": transfer.transfer_type,
                    "minimum": transfer.minimum_transfer_seconds,
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

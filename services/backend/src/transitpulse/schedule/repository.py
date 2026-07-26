# ruff: noqa: E501
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from transitpulse.schedule.models import (
    Agency,
    Route,
    Schedule,
    Service,
    Stop,
    StopTime,
    Transfer,
    Trip,
)


async def load_active_schedule(
    engine: AsyncEngine, import_status: str = "ACTIVE"
) -> Schedule | None:
    """Load the latest active or immediately preceding GTFS version."""
    if import_status not in {"ACTIVE", "SUPERSEDED"}:
        raise ValueError("STATIC_FEED_STATUS_INVALID")
    async with engine.connect() as connection:
        version_row = (
            (
                await connection.execute(
                    text(
                        "SELECT feed_version_id, feed_label, payload_checksum "
                        "FROM static_feed_versions WHERE import_status = :status "
                        "ORDER BY retrieved_at DESC LIMIT 1"
                    ),
                    {"status": import_status},
                )
            )
            .mappings()
            .first()
        )
        if version_row is None:
            return None
        version_id = str(version_row["feed_version_id"])
        schedule = Schedule(
            version=str(version_row["feed_label"]), checksum=str(version_row["payload_checksum"])
        )
        agencies = await connection.execute(
            text("SELECT agency_id, name, timezone FROM agencies WHERE feed_version_id = :version"),
            {"version": version_id},
        )
        schedule.agencies = {
            str(row.agency_id): Agency(str(row.agency_id), str(row.name), str(row.timezone))
            for row in agencies
        }
        routes = await connection.execute(
            text(
                "SELECT route_id, short_name, long_name, route_type, source_color FROM routes WHERE feed_version_id = :version"
            ),
            {"version": version_id},
        )
        schedule.routes = {
            str(row.route_id): Route(
                str(row.route_id), row.short_name, row.long_name, row.route_type, row.source_color
            )
            for row in routes
        }
        stops = await connection.execute(
            text(
                "SELECT stop_id, name, latitude, longitude FROM stops WHERE feed_version_id = :version"
            ),
            {"version": version_id},
        )
        schedule.stops = {
            str(row.stop_id): Stop(str(row.stop_id), str(row.name), row.latitude, row.longitude)
            for row in stops
        }
        services = await connection.execute(
            text(
                "SELECT service_id, monday, tuesday, wednesday, thursday, friday, saturday, sunday, start_date, end_date FROM services WHERE feed_version_id = :version"
            ),
            {"version": version_id},
        )
        schedule.services = {
            str(row.service_id): Service(
                str(row.service_id),
                (
                    row.monday,
                    row.tuesday,
                    row.wednesday,
                    row.thursday,
                    row.friday,
                    row.saturday,
                    row.sunday,
                ),
                row.start_date,
                row.end_date,
            )
            for row in services
        }
        exceptions = await connection.execute(
            text(
                "SELECT service_id, service_date, is_added FROM service_exceptions WHERE feed_version_id = :version"
            ),
            {"version": version_id},
        )
        schedule.exceptions = {
            (str(row.service_id), row.service_date): row.is_added for row in exceptions
        }
        trips = await connection.execute(
            text(
                "SELECT trip_id, route_id, service_id, shape_id, headsign, direction_id FROM trips WHERE feed_version_id = :version"
            ),
            {"version": version_id},
        )
        schedule.trips = {
            str(row.trip_id): Trip(
                str(row.trip_id),
                str(row.route_id),
                str(row.service_id),
                row.shape_id,
                row.headsign,
                row.direction_id,
            )
            for row in trips
        }
        stop_times = await connection.execute(
            text(
                "SELECT trip_id, stop_id, stop_sequence, arrival_seconds, departure_seconds FROM stop_times WHERE feed_version_id = :version"
            ),
            {"version": version_id},
        )
        schedule.stop_times = [
            StopTime(
                str(row.trip_id),
                str(row.stop_id),
                row.stop_sequence,
                row.arrival_seconds,
                row.departure_seconds,
            )
            for row in stop_times
        ]
        points = await connection.execute(
            text(
                "SELECT shape_id, sequence, latitude, longitude FROM shape_points WHERE feed_version_id = :version ORDER BY shape_id, sequence"
            ),
            {"version": version_id},
        )
        for row in points:
            schedule.shapes.setdefault(str(row.shape_id), []).append(
                (row.sequence, row.latitude, row.longitude)
            )
        transfers = await connection.execute(
            text(
                "SELECT from_stop_id, to_stop_id, transfer_type, minimum_transfer_seconds FROM transfers WHERE feed_version_id = :version"
            ),
            {"version": version_id},
        )
        schedule.transfers = [
            Transfer(
                str(row.from_stop_id),
                str(row.to_stop_id),
                row.transfer_type,
                row.minimum_transfer_seconds,
            )
            for row in transfers
        ]
        return schedule

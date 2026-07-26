from dataclasses import dataclass
from datetime import date, timedelta
from zoneinfo import ZoneInfo

from transitpulse.realtime import TripUpdate, Vehicle
from transitpulse.schedule.models import Schedule, Trip


@dataclass(frozen=True)
class Reconciliation:
    state: str
    reason: str | None
    feed_version: str | None

    @property
    def confidence(self) -> str:
        return {"MATCHED": "HIGH", "PARTIAL": "MEDIUM", "REALTIME_ADDED": "LOW"}.get(
            self.state, "NONE"
        )


def _best(results: list[Reconciliation]) -> Reconciliation:
    rank = {"MATCHED": 0, "REALTIME_ADDED": 1, "PARTIAL": 2, "UNRECONCILED": 3}
    return min(results, key=lambda result: rank[result.state])


def _service_matches(
    schedule: Schedule,
    trip: Trip,
    value: Vehicle | TripUpdate,
) -> bool:
    if not schedule.services or trip.service_id not in schedule.services:
        return True
    candidates: list[date] = []
    if value.start_date:
        candidates.append(value.start_date)
    elif value.source_timestamp if isinstance(value, Vehicle) else value.timestamp:
        moment = value.source_timestamp if isinstance(value, Vehicle) else value.timestamp
        if moment:
            agency = next(iter(schedule.agencies.values()), None)
            local_date = moment.astimezone(
                ZoneInfo(agency.timezone if agency else "America/New_York")
            ).date()
            candidates.extend([local_date, local_date - timedelta(days=1)])
    return not candidates or any(
        trip.service_id in schedule.active_service_ids(candidate) for candidate in candidates
    )


def _vehicle_against(value: Vehicle, schedule: Schedule) -> Reconciliation:
    if value.route_id and value.route_id not in schedule.routes:
        return Reconciliation("UNRECONCILED", "ROUTE_UNRECONCILED", schedule.version)
    if value.trip_id and value.trip_id not in schedule.trips:
        return Reconciliation("PARTIAL", "TRIP_UNRECONCILED", schedule.version)
    if value.trip_id:
        trip = schedule.trips[value.trip_id]
        if value.route_id and trip.route_id != value.route_id:
            return Reconciliation("PARTIAL", "TRIP_ROUTE_MISMATCH", schedule.version)
        if (
            value.direction_id is not None
            and trip.direction_id is not None
            and trip.direction_id != value.direction_id
        ):
            return Reconciliation("PARTIAL", "DIRECTION_UNRECONCILED", schedule.version)
        if not _service_matches(schedule, trip, value):
            return Reconciliation("PARTIAL", "SERVICE_DATE_UNRECONCILED", schedule.version)
    return Reconciliation("MATCHED", None, schedule.version)


def reconcile_vehicle(
    value: Vehicle,
    schedule: Schedule | None,
    previous_schedule: Schedule | None = None,
) -> Reconciliation:
    if schedule is None and previous_schedule is None:
        return Reconciliation("UNRECONCILED", "STATIC_FEED_UNAVAILABLE", None)
    results = [
        _vehicle_against(value, candidate)
        for candidate in (schedule, previous_schedule)
        if candidate is not None
    ]
    return _best(results)


def _trip_update_against(value: TripUpdate, schedule: Schedule) -> Reconciliation:
    if value.trip_id not in schedule.trips and value.relationship not in {"3", "ADDED"}:
        return Reconciliation("UNRECONCILED", "TRIP_UNRECONCILED", schedule.version)
    if value.relationship in {"3", "ADDED"}:
        return Reconciliation("REALTIME_ADDED", "REALTIME_ADDED_TRIP", schedule.version)
    missing_stops = [
        item.stop_id for item in value.predictions if item.stop_id not in schedule.stops
    ]
    if missing_stops:
        return Reconciliation("PARTIAL", "STOP_UNRECONCILED", schedule.version)
    trip = schedule.trips[value.trip_id]
    if value.route_id and trip.route_id != value.route_id:
        return Reconciliation("PARTIAL", "TRIP_ROUTE_MISMATCH", schedule.version)
    if (
        value.direction_id is not None
        and trip.direction_id is not None
        and trip.direction_id != value.direction_id
    ):
        return Reconciliation("PARTIAL", "DIRECTION_UNRECONCILED", schedule.version)
    if not _service_matches(schedule, trip, value):
        return Reconciliation("PARTIAL", "SERVICE_DATE_UNRECONCILED", schedule.version)
    return Reconciliation("MATCHED", None, schedule.version)


def reconcile_trip_update(
    value: TripUpdate,
    schedule: Schedule | None,
    previous_schedule: Schedule | None = None,
) -> Reconciliation:
    if schedule is None and previous_schedule is None:
        return Reconciliation("UNRECONCILED", "STATIC_FEED_UNAVAILABLE", None)
    results = [
        _trip_update_against(value, candidate)
        for candidate in (schedule, previous_schedule)
        if candidate is not None
    ]
    return _best(results)

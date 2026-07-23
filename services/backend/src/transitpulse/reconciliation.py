from dataclasses import dataclass

from transitpulse.realtime import TripUpdate, Vehicle
from transitpulse.schedule.models import Schedule


@dataclass(frozen=True)
class Reconciliation:
    state: str
    reason: str | None
    feed_version: str | None


def reconcile_vehicle(value: Vehicle, schedule: Schedule | None) -> Reconciliation:
    if schedule is None:
        return Reconciliation("UNRECONCILED", "STATIC_FEED_UNAVAILABLE", None)
    if value.route_id and value.route_id not in schedule.routes:
        return Reconciliation("UNRECONCILED", "ROUTE_UNRECONCILED", schedule.version)
    if value.trip_id and value.trip_id not in schedule.trips:
        return Reconciliation("PARTIAL", "TRIP_UNRECONCILED", schedule.version)
    return Reconciliation("MATCHED", None, schedule.version)


def reconcile_trip_update(value: TripUpdate, schedule: Schedule | None) -> Reconciliation:
    if schedule is None:
        return Reconciliation("UNRECONCILED", "STATIC_FEED_UNAVAILABLE", None)
    if value.trip_id not in schedule.trips and value.relationship not in {"3", "ADDED"}:
        return Reconciliation("UNRECONCILED", "TRIP_UNRECONCILED", schedule.version)
    if value.relationship in {"3", "ADDED"}:
        return Reconciliation("REALTIME_ADDED", "REALTIME_ADDED_TRIP", schedule.version)
    return Reconciliation("MATCHED", None, schedule.version)

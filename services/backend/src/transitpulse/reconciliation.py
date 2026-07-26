from dataclasses import dataclass

from transitpulse.realtime import TripUpdate, Vehicle
from transitpulse.schedule.models import Schedule


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


def reconcile_vehicle(value: Vehicle, schedule: Schedule | None) -> Reconciliation:
    if schedule is None:
        return Reconciliation("UNRECONCILED", "STATIC_FEED_UNAVAILABLE", None)
    if value.route_id and value.route_id not in schedule.routes:
        return Reconciliation("UNRECONCILED", "ROUTE_UNRECONCILED", schedule.version)
    if value.trip_id and value.trip_id not in schedule.trips:
        return Reconciliation("PARTIAL", "TRIP_UNRECONCILED", schedule.version)
    if (
        value.trip_id
        and value.route_id
        and schedule.trips[value.trip_id].route_id != value.route_id
    ):
        return Reconciliation("PARTIAL", "TRIP_ROUTE_MISMATCH", schedule.version)
    return Reconciliation("MATCHED", None, schedule.version)


def reconcile_trip_update(value: TripUpdate, schedule: Schedule | None) -> Reconciliation:
    if schedule is None:
        return Reconciliation("UNRECONCILED", "STATIC_FEED_UNAVAILABLE", None)
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
    return Reconciliation("MATCHED", None, schedule.version)

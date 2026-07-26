# pyright: reportMissingTypeStubs=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownParameterType=false, reportAttributeAccessIssue=false
"""Small, testable GTFS-Realtime normalization and current-state projection."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from google.transit import gtfs_realtime_pb2


@dataclass(frozen=True)
class Vehicle:
    entity_id: str
    vehicle_id: str
    route_id: str | None
    trip_id: str | None
    latitude: float
    longitude: float
    source_timestamp: datetime | None
    retrieved_at: datetime | None = None
    direction_id: int | None = None
    start_date: date | None = None


@dataclass(frozen=True)
class StopPrediction:
    stop_id: str
    stop_sequence: int | None
    arrival_time: datetime | None
    departure_time: datetime | None
    relationship: str
    arrival_delay_seconds: int | None = None
    departure_delay_seconds: int | None = None


@dataclass(frozen=True)
class TripUpdate:
    entity_id: str
    trip_id: str
    route_id: str | None
    vehicle_id: str | None
    timestamp: datetime | None
    relationship: str
    predictions: tuple[StopPrediction, ...] = ()
    retrieved_at: datetime | None = None
    direction_id: int | None = None
    start_date: date | None = None


@dataclass(frozen=True)
class Alert:
    entity_id: str
    header: str | None
    route_ids: tuple[str, ...]
    stop_ids: tuple[str, ...]
    retrieved_at: datetime | None = None
    source_timestamp: datetime | None = None


class RealtimeValidationError(ValueError):
    pass


MAX_FUTURE_SOURCE_SKEW = timedelta(minutes=5)
STALE_ENTITY_AGE = timedelta(seconds=90)


@dataclass
class EntityCounts:
    rejected: int = 0
    partial: int = 0
    stale: int = 0
    duplicates: int = 0

    def as_dict(self) -> dict[str, int]:
        return {
            "rejected": self.rejected,
            "partial": self.partial,
            "stale": self.stale,
            "duplicates": self.duplicates,
        }


def _feed(payload: bytes) -> gtfs_realtime_pb2.FeedMessage:
    feed = gtfs_realtime_pb2.FeedMessage()
    try:
        feed.ParseFromString(payload)
    except Exception as error:
        raise RealtimeValidationError("PROTOBUF_INVALID") from error
    if feed.header.gtfs_realtime_version != "2.0":
        raise RealtimeValidationError("FEED_HEADER_INVALID")
    if feed.header.incrementality not in {
        gtfs_realtime_pb2.FeedHeader.FULL_DATASET,
        gtfs_realtime_pb2.FeedHeader.DIFFERENTIAL,
    }:
        raise RealtimeValidationError("FEED_INCREMENTALITY_INVALID")
    return feed  # pyright: ignore[reportUnknownVariableType]


def _source_timestamp(value: int) -> datetime | None:
    if not value:
        return None
    timestamp = datetime.fromtimestamp(value, UTC)
    return None if timestamp > datetime.now(UTC) + MAX_FUTURE_SOURCE_SKEW else timestamp


def _service_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y%m%d").date()
    except ValueError:
        return None


def parse_vehicle_positions(
    payload: bytes, diagnostics: EntityCounts | None = None
) -> list[Vehicle]:
    feed = _feed(payload)
    vehicles: list[Vehicle] = []
    seen: set[str] = set()
    for entity in feed.entity:
        if not entity.id or not entity.HasField("vehicle"):
            if diagnostics:
                diagnostics.rejected += 1
            continue
        vehicle = entity.vehicle
        if not vehicle.vehicle.id or not vehicle.HasField("position"):
            if diagnostics:
                diagnostics.rejected += 1
            continue
        if entity.id in seen:
            if diagnostics:
                diagnostics.duplicates += 1
            continue
        seen.add(entity.id)
        latitude, longitude = vehicle.position.latitude, vehicle.position.longitude
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            if diagnostics:
                diagnostics.rejected += 1
            continue
        timestamp = _source_timestamp(vehicle.timestamp)
        if vehicle.timestamp and timestamp is None:
            if diagnostics:
                diagnostics.rejected += 1
            continue
        if diagnostics and (not vehicle.trip.route_id or not vehicle.trip.trip_id):
            diagnostics.partial += 1
        if diagnostics and timestamp and datetime.now(UTC) - timestamp > STALE_ENTITY_AGE:
            diagnostics.stale += 1
        vehicles.append(
            Vehicle(
                entity.id,
                vehicle.vehicle.id,
                vehicle.trip.route_id or None,
                vehicle.trip.trip_id or None,
                latitude,
                longitude,
                timestamp,
                None,
                vehicle.trip.direction_id if vehicle.trip.HasField("direction_id") else None,
                _service_date(vehicle.trip.start_date),
            )
        )
    return vehicles


def parse_trip_updates(payload: bytes, diagnostics: EntityCounts | None = None) -> list[TripUpdate]:
    feed = _feed(payload)
    results: list[TripUpdate] = []
    seen: set[str] = set()
    for entity in feed.entity:
        if (
            not entity.id
            or not entity.HasField("trip_update")
            or not entity.trip_update.trip.trip_id
        ):
            if diagnostics:
                diagnostics.rejected += 1
            continue
        if entity.id in seen:
            if diagnostics:
                diagnostics.duplicates += 1
            continue
        seen.add(entity.id)
        update = entity.trip_update
        predictions: list[StopPrediction] = []
        for stop_time in update.stop_time_update:
            if not stop_time.stop_id:
                if diagnostics:
                    diagnostics.partial += 1
                continue
            predictions.append(
                StopPrediction(
                    stop_time.stop_id,
                    stop_time.stop_sequence or None,
                    datetime.fromtimestamp(stop_time.arrival.time, UTC)
                    if stop_time.arrival.time
                    else None,
                    datetime.fromtimestamp(stop_time.departure.time, UTC)
                    if stop_time.departure.time
                    else None,
                    str(stop_time.schedule_relationship),
                    stop_time.arrival.delay if stop_time.arrival.HasField("delay") else None,
                    stop_time.departure.delay if stop_time.departure.HasField("delay") else None,
                )
            )
        timestamp = _source_timestamp(update.timestamp)
        if update.timestamp and timestamp is None:
            if diagnostics:
                diagnostics.rejected += 1
            continue
        if diagnostics and (not update.trip.route_id or not update.stop_time_update):
            diagnostics.partial += 1
        if diagnostics and timestamp and datetime.now(UTC) - timestamp > STALE_ENTITY_AGE:
            diagnostics.stale += 1
        results.append(
            TripUpdate(
                entity.id,
                update.trip.trip_id,
                update.trip.route_id or None,
                update.vehicle.id or None,
                timestamp,
                str(update.trip.schedule_relationship),
                tuple(predictions),
                None,
                update.trip.direction_id if update.trip.HasField("direction_id") else None,
                _service_date(update.trip.start_date),
            )
        )
    return results


def parse_alerts(payload: bytes, diagnostics: EntityCounts | None = None) -> list[Alert]:
    feed = _feed(payload)
    feed_timestamp = _source_timestamp(feed.header.timestamp)
    results: list[Alert] = []
    seen: set[str] = set()
    for entity in feed.entity:
        if not entity.id or not entity.HasField("alert"):
            if diagnostics:
                diagnostics.rejected += 1
            continue
        if entity.id in seen:
            if diagnostics:
                diagnostics.duplicates += 1
            continue
        seen.add(entity.id)
        alert = entity.alert
        header = alert.header_text.translation[0].text if alert.header_text.translation else None
        if diagnostics and (not header or not alert.informed_entity):
            diagnostics.partial += 1
        results.append(
            Alert(
                entity.id,
                header,
                tuple(item.route_id for item in alert.informed_entity if item.route_id),
                tuple(item.stop_id for item in alert.informed_entity if item.stop_id),
                None,
                feed_timestamp,
            )
        )
    return results


class CurrentState:
    def __init__(self, vehicle_ttl_seconds: int = 180) -> None:
        self.vehicles: dict[str, Vehicle] = {}
        self.vehicle_ttl_seconds = vehicle_ttl_seconds
        self.trip_updates: dict[str, TripUpdate] = {}
        self.alerts: dict[str, Alert] = {}

    def update_vehicles(self, candidates: list[Vehicle]) -> list[Vehicle]:
        changed: list[Vehicle] = []
        for candidate in candidates:
            existing = self.vehicles.get(candidate.vehicle_id)
            if (
                existing
                and existing.source_timestamp
                and candidate.source_timestamp
                and candidate.source_timestamp < existing.source_timestamp
            ):
                continue
            if existing != candidate:
                self.vehicles[candidate.vehicle_id] = candidate
                changed.append(candidate)
        return changed

    def route_vehicles(self, route_id: str) -> list[Vehicle]:
        return sorted(
            (item for item in self.vehicles.values() if item.route_id == route_id),
            key=lambda item: item.vehicle_id,
        )

    def expire(self, now: datetime) -> list[str]:
        expired = [
            key
            for key, value in self.vehicles.items()
            if value.source_timestamp
            and (now - value.source_timestamp).total_seconds() > self.vehicle_ttl_seconds
        ]
        for key in expired:
            del self.vehicles[key]
        return expired

    def update_trip_updates(self, values: list[TripUpdate]) -> list[TripUpdate]:
        changed: list[TripUpdate] = []
        for item in values:
            existing = self.trip_updates.get(item.trip_id)
            if (
                existing
                and existing.timestamp
                and item.timestamp
                and item.timestamp < existing.timestamp
            ):
                continue
            if existing != item:
                self.trip_updates[item.trip_id] = item
                changed.append(item)
        return changed

    def update_alerts(self, values: list[Alert]) -> None:
        self.alerts.update({item.entity_id: item for item in values})

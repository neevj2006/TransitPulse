# pyright: reportMissingTypeStubs=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
"""Small, testable GTFS-Realtime normalization and current-state projection."""

from dataclasses import dataclass
from datetime import UTC, datetime

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


class RealtimeValidationError(ValueError):
    pass


def parse_vehicle_positions(payload: bytes) -> list[Vehicle]:
    feed = gtfs_realtime_pb2.FeedMessage()
    try:
        feed.ParseFromString(payload)
    except Exception as error:
        raise RealtimeValidationError("PROTOBUF_INVALID") from error
    vehicles: list[Vehicle] = []
    for entity in feed.entity:
        if not entity.id or not entity.HasField("vehicle"):
            continue
        vehicle = entity.vehicle
        if not vehicle.vehicle.id or not vehicle.HasField("position"):
            continue
        latitude, longitude = vehicle.position.latitude, vehicle.position.longitude
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            continue
        timestamp = datetime.fromtimestamp(vehicle.timestamp, UTC) if vehicle.timestamp else None
        vehicles.append(
            Vehicle(
                entity.id,
                vehicle.vehicle.id,
                vehicle.trip.route_id or None,
                vehicle.trip.trip_id or None,
                latitude,
                longitude,
                timestamp,
            )
        )
    return vehicles


class CurrentState:
    def __init__(self) -> None:
        self.vehicles: dict[str, Vehicle] = {}

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

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class Agency:
    agency_id: str
    name: str
    timezone: str


@dataclass(frozen=True)
class Route:
    route_id: str
    short_name: str | None
    long_name: str | None
    route_type: int
    color: str | None = None


@dataclass(frozen=True)
class Stop:
    stop_id: str
    name: str
    latitude: float | None
    longitude: float | None
    parent_station: str | None = None


@dataclass(frozen=True)
class Trip:
    trip_id: str
    route_id: str
    service_id: str
    shape_id: str | None
    headsign: str | None


@dataclass(frozen=True)
class StopTime:
    trip_id: str
    stop_id: str
    sequence: int
    arrival_seconds: int | None
    departure_seconds: int | None


@dataclass(frozen=True)
class Transfer:
    from_stop_id: str
    to_stop_id: str
    transfer_type: int
    minimum_transfer_seconds: int | None


@dataclass(frozen=True)
class Service:
    service_id: str
    weekdays: tuple[bool, bool, bool, bool, bool, bool, bool]
    start_date: date
    end_date: date


@dataclass
class Schedule:
    version: str
    checksum: str
    routes: dict[str, Route] = field(default_factory=lambda: {})
    agencies: dict[str, Agency] = field(default_factory=lambda: {})
    stops: dict[str, Stop] = field(default_factory=lambda: {})
    trips: dict[str, Trip] = field(default_factory=lambda: {})
    stop_times: list[StopTime] = field(default_factory=lambda: [])
    services: dict[str, Service] = field(default_factory=lambda: {})
    exceptions: dict[tuple[str, date], bool] = field(default_factory=lambda: {})
    shapes: dict[str, list[tuple[int, float, float]]] = field(default_factory=lambda: {})
    transfers: list[Transfer] = field(default_factory=lambda: [])
    warnings: list[str] = field(default_factory=lambda: [])

    def import_statistics(self) -> dict[str, int]:
        return {
            "agencies": len(self.agencies),
            "routes": len(self.routes),
            "stops": len(self.stops),
            "services": len(self.services),
            "trips": len(self.trips),
            "stop_times": len(self.stop_times),
            "shape_points": sum(len(points) for points in self.shapes.values()),
            "transfers": len(self.transfers),
        }

    def active_service_ids(self, service_date: date) -> set[str]:
        active: set[str] = set()
        for service in self.services.values():
            exception = self.exceptions.get((service.service_id, service_date))
            if exception is True:
                active.add(service.service_id)
            elif (
                exception is not False
                and service.start_date <= service_date <= service.end_date
                and service.weekdays[service_date.weekday()]
            ):
                active.add(service.service_id)
        return active

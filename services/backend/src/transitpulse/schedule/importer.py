import csv
import hashlib
import io
import re
import zipfile
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import PurePosixPath

import httpx

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

REQUIRED_FILES = {"agency.txt", "routes.txt", "stops.txt", "trips.txt", "stop_times.txt"}
MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
MAX_EXTRACTED_BYTES = 500 * 1024 * 1024
MAX_FILE_BYTES = 100 * 1024 * 1024


class GtfsValidationError(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code


@dataclass(frozen=True)
class DownloadedArchive:
    payload: bytes
    source_url: str
    retrieved_at: str
    checksum: str


async def download_archive(
    url: str, client: httpx.AsyncClient, maximum_bytes: int = MAX_ARCHIVE_BYTES
) -> DownloadedArchive:
    try:
        async with client.stream(
            "GET",
            url,
            headers={"User-Agent": "TransitPulse/0.1 (https://github.com/neevj2006/TransitPulse)"},
            timeout=httpx.Timeout(15, read=45),
        ) as response:
            response.raise_for_status()
            payload = b""
            async for chunk in response.aiter_bytes():
                payload += chunk
                if len(payload) > maximum_bytes:
                    raise GtfsValidationError(
                        "PAYLOAD_TOO_LARGE", "download exceeds maximum archive size"
                    )
    except httpx.HTTPError as error:
        raise GtfsValidationError("SOURCE_HTTP_ERROR", str(error)) from error
    return DownloadedArchive(
        payload, url, datetime.now(UTC).isoformat(), hashlib.sha256(payload).hexdigest()
    )


def parse_gtfs_time(value: str) -> int | None:
    if not value:
        return None
    match = re.fullmatch(r"(\d{1,2}):(\d{2}):(\d{2})", value)
    if not match:
        raise GtfsValidationError("GTFS_TIME_INVALID", value)
    hours, minutes, seconds = map(int, match.groups())
    total = hours * 3600 + minutes * 60 + seconds
    if minutes > 59 or seconds > 59 or total > 172799:
        raise GtfsValidationError("GTFS_TIME_INVALID", value)
    return total


def _rows(zf: zipfile.ZipFile, filename: str) -> list[dict[str, str]]:
    try:
        with zf.open(filename) as file:
            return list(csv.DictReader(io.TextIOWrapper(file, encoding="utf-8-sig", newline="")))
    except KeyError:
        return []


def _date(value: str) -> date:
    try:
        return date.fromisoformat(f"{value[:4]}-{value[4:6]}-{value[6:8]}")
    except ValueError as error:
        raise GtfsValidationError("GTFS_DATE_INVALID", value) from error


def _coordinate(value: str, lower: float, upper: float, field: str) -> float | None:
    if not value:
        return None
    try:
        number = float(value)
    except ValueError as error:
        raise GtfsValidationError("COORDINATE_INVALID", f"{field}={value}") from error
    if not lower <= number <= upper:
        raise GtfsValidationError("COORDINATE_INVALID", f"{field}={value}")
    return number


def import_archive(payload: bytes) -> Schedule:
    if len(payload) > MAX_ARCHIVE_BYTES:
        raise GtfsValidationError("PAYLOAD_TOO_LARGE", "archive exceeds maximum size")
    try:
        zf = zipfile.ZipFile(io.BytesIO(payload))
    except zipfile.BadZipFile as error:
        raise GtfsValidationError("ZIP_INVALID", "not a ZIP archive") from error
    with zf:
        names = set(zf.namelist())
        unsafe = [
            name
            for name in names
            if PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts
        ]
        if unsafe:
            raise GtfsValidationError("ZIP_UNSAFE_PATH", unsafe[0])
        total = 0
        for info in zf.infolist():
            if info.is_dir():
                continue
            if info.file_size > MAX_FILE_BYTES:
                raise GtfsValidationError("ZIP_EXPANSION_LIMIT", info.filename)
            total += info.file_size
        if total > MAX_EXTRACTED_BYTES:
            raise GtfsValidationError("ZIP_EXPANSION_LIMIT", "archive extracted size")
        missing = REQUIRED_FILES - names
        if missing:
            raise GtfsValidationError("GTFS_REQUIRED_FILE_MISSING", ", ".join(sorted(missing)))
        checksum = hashlib.sha256(payload).hexdigest()
        feed_info = _rows(zf, "feed_info.txt")
        version = feed_info[0].get("feed_version") if feed_info else None
        schedule = Schedule(version=version or checksum[:12], checksum=checksum)
        for row in _rows(zf, "agency.txt"):
            agency_id = row.get("agency_id") or "default"
            name, timezone = row.get("agency_name", ""), row.get("agency_timezone", "")
            if not name or not timezone:
                raise GtfsValidationError("REFERENCE_MISSING", "agency_name or agency_timezone")
            schedule.agencies[agency_id] = Agency(agency_id, name, timezone)
        for row in _rows(zf, "routes.txt"):
            route_id = row.get("route_id", "")
            if not route_id:
                raise GtfsValidationError("REFERENCE_MISSING", "route_id")
            color = row.get("route_color") or None
            if color and not re.fullmatch(r"[0-9A-Fa-f]{6}", color):
                raise GtfsValidationError("ROUTE_COLOR_INVALID", route_id)
            schedule.routes[route_id] = Route(
                route_id,
                row.get("route_short_name") or None,
                row.get("route_long_name") or None,
                int(row.get("route_type") or 3),
                color.upper() if color else None,
            )
        for row in _rows(zf, "stops.txt"):
            stop_id = row.get("stop_id", "")
            if not stop_id or not row.get("stop_name"):
                raise GtfsValidationError("REFERENCE_MISSING", "stop_id or stop_name")
            schedule.stops[stop_id] = Stop(
                stop_id,
                row["stop_name"],
                _coordinate(row.get("stop_lat", ""), -90, 90, "stop_lat"),
                _coordinate(row.get("stop_lon", ""), -180, 180, "stop_lon"),
                row.get("parent_station") or None,
            )
        for stop in schedule.stops.values():
            if stop.parent_station and stop.parent_station not in schedule.stops:
                raise GtfsValidationError(
                    "REFERENCE_MISSING", f"parent_station {stop.parent_station}"
                )
        for row in _rows(zf, "calendar.txt"):
            service_id = row.get("service_id", "")
            if not service_id:
                raise GtfsValidationError("REFERENCE_MISSING", "service_id")
            weekdays = tuple(
                row.get(day, "0") == "1"
                for day in (
                    "monday",
                    "tuesday",
                    "wednesday",
                    "thursday",
                    "friday",
                    "saturday",
                    "sunday",
                )
            )
            schedule.services[service_id] = Service(
                service_id,
                (
                    weekdays[0],
                    weekdays[1],
                    weekdays[2],
                    weekdays[3],
                    weekdays[4],
                    weekdays[5],
                    weekdays[6],
                ),
                _date(row["start_date"]),
                _date(row["end_date"]),
            )
        for row in _rows(zf, "calendar_dates.txt"):
            service_id = row.get("service_id", "")
            if not service_id:
                raise GtfsValidationError("REFERENCE_MISSING", "calendar_dates service_id")
            schedule.exceptions[(service_id, _date(row["date"]))] = row.get("exception_type") == "1"
        for row in _rows(zf, "trips.txt"):
            trip_id, route_id, service_id = (
                row.get("trip_id", ""),
                row.get("route_id", ""),
                row.get("service_id", ""),
            )
            if route_id not in schedule.routes or not service_id:
                raise GtfsValidationError("REFERENCE_MISSING", f"trip {trip_id}")
            schedule.trips[trip_id] = Trip(
                trip_id,
                route_id,
                service_id,
                row.get("shape_id") or None,
                row.get("trip_headsign") or None,
            )
        previous: dict[str, int] = {}
        for row in _rows(zf, "stop_times.txt"):
            trip_id, stop_id = row.get("trip_id", ""), row.get("stop_id", "")
            sequence = int(row.get("stop_sequence") or 0)
            if (
                trip_id not in schedule.trips
                or stop_id not in schedule.stops
                or sequence <= previous.get(trip_id, 0)
            ):
                raise GtfsValidationError("REFERENCE_MISSING", f"stop time {trip_id}:{sequence}")
            previous[trip_id] = sequence
            schedule.stop_times.append(
                StopTime(
                    trip_id,
                    stop_id,
                    sequence,
                    parse_gtfs_time(row.get("arrival_time", "")),
                    parse_gtfs_time(row.get("departure_time", "")),
                )
            )
        for row in _rows(zf, "shapes.txt"):
            shape_id = row.get("shape_id", "")
            sequence = int(row.get("shape_pt_sequence") or 0)
            points = schedule.shapes.setdefault(shape_id, [])
            if points and sequence <= points[-1][0]:
                raise GtfsValidationError("SHAPE_SEQUENCE_INVALID", shape_id)
            points.append(
                (
                    sequence,
                    _coordinate(row.get("shape_pt_lat", ""), -90, 90, "shape_pt_lat") or 0.0,
                    _coordinate(row.get("shape_pt_lon", ""), -180, 180, "shape_pt_lon") or 0.0,
                )
            )
        for row in _rows(zf, "transfers.txt"):
            from_stop, to_stop = row.get("from_stop_id", ""), row.get("to_stop_id", "")
            if from_stop not in schedule.stops or to_stop not in schedule.stops:
                raise GtfsValidationError("REFERENCE_MISSING", f"transfer {from_stop}:{to_stop}")
            try:
                transfer_type = int(row.get("transfer_type") or 0)
                minimum = int(row["min_transfer_time"]) if row.get("min_transfer_time") else None
            except ValueError as error:
                raise GtfsValidationError(
                    "TRANSFER_INVALID", f"transfer {from_stop}:{to_stop}"
                ) from error
            if transfer_type not in {0, 1, 2, 3} or (minimum is not None and minimum < 0):
                raise GtfsValidationError("TRANSFER_INVALID", f"transfer {from_stop}:{to_stop}")
            schedule.transfers.append(Transfer(from_stop, to_stop, transfer_type, minimum))
        return schedule

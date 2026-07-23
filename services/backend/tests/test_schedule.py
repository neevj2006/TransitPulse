# ruff: noqa: E501
import io
import zipfile
from collections.abc import AsyncGenerator
from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient

from transitpulse.app import create_app
from transitpulse.config import Settings
from transitpulse.schedule.importer import GtfsValidationError, import_archive, parse_gtfs_time


def archive(files: dict[str, str]) -> bytes:
    result = io.BytesIO()
    with zipfile.ZipFile(result, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return result.getvalue()


def fixture() -> bytes:
    return archive(
        {
            "agency.txt": "agency_id,agency_name,agency_url,agency_timezone\nMBTA,MBTA,https://mbta.com,America/New_York\n",
            "feed_info.txt": "feed_version\ntest-v1\n",
            "routes.txt": "route_id,route_short_name,route_long_name,route_type,route_color\nRed,Red,Red Line,1,DA291C\n",
            "stops.txt": "stop_id,stop_name,stop_lat,stop_lon\nA,Alpha,42.1,-71.1\nB,Beta,42.2,-71.2\n",
            "calendar.txt": "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\nweekday,1,1,1,1,1,0,0,20260701,20260731\n",
            "calendar_dates.txt": "service_id,date,exception_type\nweekday,20260725,1\nweekday,20260728,2\n",
            "trips.txt": "route_id,service_id,trip_id,trip_headsign,shape_id\nRed,weekday,t1,Alewife,s1\n",
            "stop_times.txt": "trip_id,arrival_time,departure_time,stop_id,stop_sequence\nt1,23:59:00,23:59:00,A,1\nt1,24:05:00,24:05:00,B,2\n",
            "shapes.txt": "shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence\ns1,42.1,-71.1,1\ns1,42.2,-71.2,2\n",
        }
    )


def test_import_preserves_after_midnight_time_and_exceptions() -> None:
    schedule = import_archive(fixture())
    assert schedule.version == "test-v1"
    assert schedule.stop_times[-1].arrival_seconds == 86700
    assert schedule.active_service_ids(date(2026, 7, 25)) == {"weekday"}
    assert schedule.active_service_ids(date(2026, 7, 28)) == set()


@pytest.mark.parametrize(
    "payload,code",
    [
        (archive({"../routes.txt": "x"}), "ZIP_UNSAFE_PATH"),
        (archive({"agency.txt": "x"}), "GTFS_REQUIRED_FILE_MISSING"),
    ],
)
def test_rejects_unsafe_or_incomplete_archives(payload: bytes, code: str) -> None:
    with pytest.raises(GtfsValidationError, match=code):
        import_archive(payload)


def test_rejects_invalid_gtfs_time() -> None:
    with pytest.raises(GtfsValidationError):
        parse_gtfs_time("25:61:00")


@pytest.fixture
async def schedule_client() -> AsyncGenerator[AsyncClient, None]:
    app = create_app(Settings(environment="test"), probes=[])
    app.state.schedule = import_archive(fixture())
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            yield client


async def test_schedule_routes_search_shape_and_arrivals(schedule_client: AsyncClient) -> None:
    routes = await schedule_client.get("/api/v1/routes", params={"q": "red"})
    assert routes.status_code == 200
    assert routes.json()["data"][0]["route_id"] == "Red"
    shape = await schedule_client.get("/api/v1/routes/Red/shape")
    assert shape.json()["data"]["features"][0]["geometry"]["type"] == "LineString"
    arrivals = await schedule_client.get(
        "/api/v1/stops/B/arrivals", params={"service_date": "2026-07-24"}
    )
    assert arrivals.json()["data"][0]["scheduled"]["gtfs_seconds"] == 86700

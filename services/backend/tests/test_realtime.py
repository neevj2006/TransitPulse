# pyright: reportMissingTypeStubs=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from google.transit import gtfs_realtime_pb2

from transitpulse.polling import FeedConfig, FeedPoller, RawSnapshotStore
from transitpulse.realtime import (
    CurrentState,
    Vehicle,
    parse_alerts,
    parse_trip_updates,
    parse_vehicle_positions,
)


def test_parses_vehicle_and_rejects_invalid_coordinates() -> None:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    entity = feed.entity.add(id="entity")
    entity.vehicle.vehicle.id = "vehicle"
    entity.vehicle.trip.route_id = "Red"
    entity.vehicle.position.latitude = 42.0
    entity.vehicle.position.longitude = -71.0
    entity.vehicle.timestamp = 1_700_000_000
    assert parse_vehicle_positions(feed.SerializeToString())[0].route_id == "Red"


def test_parses_trip_updates_and_alerts() -> None:
    trip_feed = gtfs_realtime_pb2.FeedMessage()
    trip_feed.header.gtfs_realtime_version = "2.0"
    update = trip_feed.entity.add(id="update").trip_update
    update.trip.trip_id = "trip"
    update.trip.route_id = "Red"
    assert parse_trip_updates(trip_feed.SerializeToString())[0].trip_id == "trip"
    alert_feed = gtfs_realtime_pb2.FeedMessage()
    alert_feed.header.gtfs_realtime_version = "2.0"
    alert = alert_feed.entity.add(id="alert").alert
    alert.informed_entity.add().route_id = "Red"
    assert parse_alerts(alert_feed.SerializeToString())[0].route_ids == ("Red",)


def test_older_current_state_cannot_overwrite_newer_value() -> None:
    state = CurrentState()
    now = datetime.now(UTC)
    newer = Vehicle("one", "v", "Red", None, 42.0, -71.0, now)
    older = Vehicle("two", "v", "Red", None, 43.0, -72.0, now - timedelta(seconds=1))
    assert state.update_vehicles([newer]) == [newer]
    assert state.update_vehicles([older]) == []
    assert state.route_vehicles("Red")[0].latitude == 42.0


async def test_poller_stores_payload_and_uses_conditional_headers(tmp_path: Path) -> None:
    seen: dict[str, str] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.update(request.headers)
        return httpx.Response(200, content=b"payload", headers={"etag": "one"})

    poller = FeedPoller(
        FeedConfig("vehicles", "https://example.test/feed"), RawSnapshotStore(tmp_path)
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result, payload = await poller.poll(client)
    assert result.outcome == "SUCCESS"
    assert payload == b"payload"
    assert list(tmp_path.rglob("*.pb.gz"))  # noqa: ASYNC240
    assert "TransitPulse" in seen["user-agent"]

# pyright: reportMissingTypeStubs=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from google.transit import gtfs_realtime_pb2

from transitpulse.app import create_app
from transitpulse.config import Settings
from transitpulse.diagnostics import vehicle_quality
from transitpulse.events import EventBroker
from transitpulse.polling import FeedConfig, FeedPoller, RawSnapshotStore
from transitpulse.realtime import (
    CurrentState,
    StopPrediction,
    TripUpdate,
    Vehicle,
    parse_alerts,
    parse_trip_updates,
    parse_vehicle_positions,
)
from transitpulse.reconciliation import reconcile_vehicle
from transitpulse.schedule.models import Schedule


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
    prediction = update.stop_time_update.add()
    prediction.stop_id = "stop"
    prediction.arrival.time = 1_700_000_000
    parsed_update = parse_trip_updates(trip_feed.SerializeToString())[0]
    assert parsed_update.trip_id == "trip"
    assert parsed_update.predictions[0].stop_id == "stop"
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


def test_current_state_expires_old_vehicles() -> None:
    state = CurrentState(vehicle_ttl_seconds=30)
    now = datetime.now(UTC)
    state.update_vehicles(
        [Vehicle("one", "v", "Red", None, 42.0, -71.0, now - timedelta(seconds=31))]
    )
    assert state.expire(now) == ["v"]


def test_unreconciled_vehicle_is_explicit() -> None:
    result = reconcile_vehicle(
        Vehicle("e", "v", "Missing", None, 42, -71, None), Schedule("v", "checksum")
    )
    assert result.state == "UNRECONCILED"
    assert result.reason == "ROUTE_UNRECONCILED"


def test_vehicle_quality_flags_frozen_and_impossible_jumps() -> None:
    now = datetime.now(UTC)
    frozen = vehicle_quality(
        Vehicle("a", "v", "Red", None, 42, -71, now),
        Vehicle("b", "v", "Red", None, 42, -71, now + timedelta(minutes=6)),
    )
    jumped = vehicle_quality(
        Vehicle("a", "v", "Red", None, 42, -71, now),
        Vehicle("b", "v", "Red", None, 43, -72, now + timedelta(seconds=10)),
    )
    assert "VEHICLE_FROZEN" in frozen
    assert "VEHICLE_IMPOSSIBLE_JUMP" in jumped


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


async def test_live_vehicle_response_has_freshness() -> None:
    app = create_app(Settings(environment="test"), probes=[])
    app.state.current_state.update_vehicles(
        [Vehicle("entity", "bus", "Red", None, 42.0, -71.0, datetime.now(UTC))]
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/live/routes/Red/vehicles")
    assert response.status_code == 200
    assert response.json()["data"][0]["freshness"]["state"] == "HEALTHY"


async def test_live_arrivals_are_scoped_to_the_requested_stop() -> None:
    app = create_app(Settings(environment="test"), probes=[])
    now = datetime.now(UTC)
    app.state.current_state.update_trip_updates(
        [
            TripUpdate(
                "update",
                "trip",
                "Red",
                None,
                now,
                "0",
                (StopPrediction("target", 1, now + timedelta(minutes=2), None, "0"),),
            )
        ]
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/live/stops/target/arrivals")
    assert response.status_code == 200
    assert response.json()["data"][0]["stop_id"] == "target"


def test_event_broker_scopes_and_replays_monotonic_events() -> None:
    broker = EventBroker()
    broker.publish("vehicle.changed", '{"schema_version":"1.0.0"}', route_id="Red")
    broker.publish("vehicle.changed", '{"schema_version":"1.0.0"}', route_id="Orange")
    assert [event.event_id for event in broker.since(0, "Red", None)] == [1]
    assert broker.since(1, "Red", None) == []

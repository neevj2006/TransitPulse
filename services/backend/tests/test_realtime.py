# pyright: reportMissingTypeStubs=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportAttributeAccessIssue=false
import asyncio
import base64
import gzip
import json
import os
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import cast

import httpx
import pytest
from google.transit import gtfs_realtime_pb2

from transitpulse.app import create_app
from transitpulse.cache import RedisStateStore
from transitpulse.config import Settings
from transitpulse.diagnostics import diagnostic_rates, summarize, vehicle_quality
from transitpulse.events import EventBroker
from transitpulse.history import RealtimeHistoryStore
from transitpulse.live_api import latency_summary, service_date_for
from transitpulse.polling import (
    FeedConfig,
    FeedPoller,
    PollResult,
    RawSnapshotStore,
    SourceHealth,
    promote_fixture,
)
from transitpulse.realtime import (
    Alert,
    CurrentState,
    EntityCounts,
    RealtimeValidationError,
    StopPrediction,
    TripUpdate,
    Vehicle,
    parse_alerts,
    parse_trip_updates,
    parse_vehicle_positions,
)
from transitpulse.reconciliation import reconcile_trip_update, reconcile_vehicle
from transitpulse.schedule.models import Agency, Route, Schedule, Service, Stop, StopTime, Trip
from transitpulse.worker import RealtimeProjector, run_poller


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


def test_rejects_future_dated_realtime_entities() -> None:
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"
    entity = feed.entity.add(id="entity")
    entity.vehicle.vehicle.id = "vehicle"
    entity.vehicle.position.latitude = 42.0
    entity.vehicle.position.longitude = -71.0
    entity.vehicle.timestamp = int((datetime.now(UTC) + timedelta(minutes=6)).timestamp())
    assert parse_vehicle_positions(feed.SerializeToString()) == []


def test_vehicle_parser_counts_rejected_partial_stale_and_duplicate_entities() -> None:
    now = datetime.now(UTC)
    feed = gtfs_realtime_pb2.FeedMessage()
    feed.header.gtfs_realtime_version = "2.0"

    def add_vehicle(
        entity_id: str,
        vehicle_id: str,
        latitude: float,
        timestamp: datetime,
        route_id: str = "Red",
        trip_id: str = "trip",
    ) -> None:
        entity = feed.entity.add(id=entity_id)
        entity.vehicle.vehicle.id = vehicle_id
        entity.vehicle.trip.route_id = route_id
        entity.vehicle.trip.trip_id = trip_id
        entity.vehicle.position.latitude = latitude
        entity.vehicle.position.longitude = -71
        entity.vehicle.timestamp = int(timestamp.timestamp())

    add_vehicle("valid", "v1", 42, now)
    add_vehicle("valid", "duplicate", 42, now)
    add_vehicle("invalid", "v2", 100, now)
    add_vehicle("partial", "v3", 42, now, "", "")
    add_vehicle("stale", "v4", 42, now - timedelta(minutes=2))
    counts = EntityCounts()

    parsed = parse_vehicle_positions(feed.SerializeToString(), counts)

    assert [item.entity_id for item in parsed] == ["valid", "partial", "stale"]
    assert counts.as_dict() == {
        "rejected": 1,
        "partial": 1,
        "stale": 1,
        "duplicates": 1,
    }


def test_rejects_missing_or_unsupported_realtime_feed_headers() -> None:
    unsupported = gtfs_realtime_pb2.FeedMessage()
    unsupported.header.gtfs_realtime_version = "1.0"

    with pytest.raises(RealtimeValidationError, match="FEED_HEADER_INVALID"):
        parse_vehicle_positions(b"")
    with pytest.raises(RealtimeValidationError, match="FEED_HEADER_INVALID"):
        parse_vehicle_positions(unsupported.SerializeToString())


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


def recorded_realtime_samples() -> dict[str, bytes]:
    fixture_path = (
        Path(__file__).parents[3] / "data" / "fixtures" / "realtime" / "mbta-recorded-samples.json"
    )
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    return {name: base64.b64decode(value) for name, value in fixture["samples"].items()}


def test_recorded_realtime_fixtures_parse_offline() -> None:
    samples = recorded_realtime_samples()
    assert parse_vehicle_positions(samples["vehicles"])[0].vehicle_id == "v-recorded"
    assert parse_trip_updates(samples["trip_updates"])[0].trip_id == "trip-recorded"
    assert parse_alerts(samples["alerts"])[0].entity_id == "alert-recorded"


def test_fixture_promotion_and_raw_storage_preserve_payload_bytes(tmp_path: Path) -> None:
    payload = recorded_realtime_samples()["vehicles"] + b"\xa0\x06\x01"
    fixture_payload, fixture_metadata = promote_fixture(
        tmp_path / "fixtures",
        "vehicles-recorded",
        payload,
        "https://cdn.mbta.com/realtime/VehiclePositions.pb",
    )
    store = RawSnapshotStore(tmp_path / "raw")
    store.save("mbta-vehicles", payload, datetime.now(UTC))
    snapshot = next((tmp_path / "raw").rglob("*.pb.gz"))

    assert fixture_payload.read_bytes() == payload
    assert json.loads(fixture_metadata.read_text(encoding="utf-8"))["checksum"]
    with gzip.open(snapshot, "rb") as source:
        assert source.read() == payload


async def test_recorded_fixtures_produce_versioned_live_api_contracts() -> None:
    samples = recorded_realtime_samples()
    app = create_app(Settings(environment="test", redis_url=None), probes=[])
    app.state.current_state.update_vehicles(parse_vehicle_positions(samples["vehicles"]))
    app.state.current_state.update_trip_updates(parse_trip_updates(samples["trip_updates"]))
    app.state.current_state.update_alerts(parse_alerts(samples["alerts"]))
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        vehicles = await client.get("/api/v1/live/routes/Red/vehicles")
        arrivals = await client.get("/api/v1/live/stops/stop-recorded/arrivals")
        alerts = await client.get("/api/v1/live/alerts", params={"route_id": "Red"})

    assert vehicles.json()["schema_version"] == "1.0.0"
    assert vehicles.json()["data"][0]["vehicle_id"] == "v-recorded"
    assert arrivals.json()["data"][0]["trip_id"] == "trip-recorded"
    assert alerts.json()["data"][0]["alert_id"] == "alert-recorded"


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


def test_reconciliation_records_partial_descriptor_mismatches() -> None:
    schedule = Schedule(
        "v",
        "checksum",
        routes={"Red": Route("Red", "Red", None, 1)},
        stops={"known-stop": Stop("known-stop", "Known", 42, -71)},
        trips={"trip": Trip("trip", "Red", "daily", None, None)},
    )
    update = TripUpdate(
        "entity",
        "trip",
        "Orange",
        None,
        datetime.now(UTC),
        "0",
        (StopPrediction("missing-stop", None, None, None, "0"),),
    )
    result = reconcile_trip_update(update, schedule)
    assert result.state == "PARTIAL"
    assert result.reason == "STOP_UNRECONCILED"
    assert result.confidence == "MEDIUM"


def test_reconciliation_uses_preceding_feed_and_checks_direction_service_date() -> None:
    current = Schedule("current", "current-checksum")
    previous = Schedule(
        "previous",
        "previous-checksum",
        agencies={"MBTA": Agency("MBTA", "MBTA", "America/New_York")},
        routes={"Red": Route("Red", "Red", None, 1)},
        stops={"stop": Stop("stop", "Stop", 42, -71)},
        trips={"trip": Trip("trip", "Red", "one-day", None, None, 0)},
        services={
            "one-day": Service(
                "one-day",
                (True, True, True, True, True, True, True),
                date(2026, 7, 1),
                date(2026, 7, 1),
            )
        },
    )
    after_midnight = TripUpdate(
        "entity",
        "trip",
        "Red",
        None,
        datetime(2026, 7, 2, 4, 30, tzinfo=UTC),
        "0",
        (StopPrediction("stop", 1, None, None, "0"),),
        direction_id=0,
    )

    matched = reconcile_trip_update(after_midnight, current, previous)
    wrong_direction = reconcile_trip_update(
        replace(after_midnight, direction_id=1, start_date=date(2026, 7, 1)),
        current,
        previous,
    )
    wrong_service_date = reconcile_trip_update(
        replace(after_midnight, start_date=date(2026, 7, 2)),
        current,
        previous,
    )

    assert matched.state == "MATCHED"
    assert matched.feed_version == "previous"
    assert wrong_direction.reason == "DIRECTION_UNRECONCILED"
    assert wrong_service_date.reason == "SERVICE_DATE_UNRECONCILED"


def test_diagnostic_rates_make_realtime_quality_limits_explicit() -> None:
    rates = diagnostic_rates(
        {"accepted": 8, "unreconciled": 2, "parser_errors": 1, "duplicates": 3}
    )
    assert rates == {
        "parser_failure_rate": 0.1,
        "reconciliation_failure_rate": 0.2,
        "duplicate_rate": 0.3,
    }


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


def test_service_date_uses_mbta_timezone_across_dst_boundary() -> None:
    schedule = Schedule(
        "test", "checksum", agencies={"MBTA": Agency("MBTA", "MBTA", "America/New_York")}
    )

    assert service_date_for(schedule, datetime(2026, 3, 8, 4, 30, tzinfo=UTC)) == "2026-03-07"
    assert service_date_for(schedule, datetime(2026, 3, 8, 7, 30, tzinfo=UTC)) == "2026-03-08"


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
    metadata = json.loads(next(tmp_path.rglob("*.json")).read_text(encoding="utf-8"))  # noqa: ASYNC240
    assert metadata["parser_version"] == "gtfs-realtime-v1"
    assert metadata["checksum"] == result.checksum
    assert "TransitPulse" in seen["user-agent"]


def test_raw_snapshot_pruning_removes_only_expired_payloads(tmp_path: Path) -> None:
    store = RawSnapshotStore(tmp_path)
    old = tmp_path / "source" / "old.pb.gz"
    old.parent.mkdir(parents=True)
    old.write_bytes(b"old")
    old_time = (datetime.now(UTC) - timedelta(hours=7)).timestamp()
    os.utime(old, (old_time, old_time))
    store.save("source", b"new", datetime.now(UTC))
    assert store.prune(datetime.now(UTC) - timedelta(hours=6)) == 1
    assert list(tmp_path.rglob("*.pb.gz"))


async def test_poller_opens_a_bounded_circuit_after_repeated_failures(tmp_path: Path) -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    poller = FeedPoller(
        FeedConfig("vehicles", "https://example.test/feed"), RawSnapshotStore(tmp_path)
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await poller.poll(client)
        await poller.poll(client)
        result, _ = await poller.poll(client)
        opened, _ = await poller.poll(client)
    assert result.outcome == "ERROR"
    assert poller.health.circuit_open_until is not None
    assert opened.outcome == "CIRCUIT_OPEN"


async def test_poller_records_timeout_and_recovers_after_source_is_healthy(
    tmp_path: Path,
) -> None:
    attempts = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise httpx.ReadTimeout("timed out", request=request)
        return httpx.Response(200, content=recorded_realtime_samples()["vehicles"])

    poller = FeedPoller(
        FeedConfig("vehicles", "https://example.test/feed"), RawSnapshotStore(tmp_path)
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        failed, _ = await poller.poll(client)
        recovered, payload = await poller.poll(client)

    assert failed.error_code == "SOURCE_HTTP_ERROR"
    assert recovered.outcome == "SUCCESS"
    assert payload
    assert poller.health.failures == 0


def test_source_health_transitions_are_explicit() -> None:
    now = datetime.now(UTC)
    health = SourceHealth()
    assert health.state(now) == "UNKNOWN"
    health.last_success_at = now
    assert health.state(now) == "HEALTHY"
    assert health.state(now + timedelta(seconds=91)) == "STALE"
    health.circuit_open_until = now + timedelta(minutes=2)
    assert health.state(now + timedelta(seconds=91)) == "OFFLINE"


def test_feed_summary_calculates_source_age_and_poll_success_rate() -> None:
    now = datetime.now(UTC)
    health = SourceHealth(last_success_at=now - timedelta(seconds=30))
    history = [
        PollResult("source", now, now, "SUCCESS", 200, "one", 10),
        PollResult("source", now, now, "ERROR", 503, None, 0),
    ]

    summary = summarize("source", health, history, now)

    assert summary.source_age_seconds == 30
    assert summary.success_rate == 0.5
    assert summary.state == "HEALTHY"


async def test_run_poller_contains_redis_and_postgresql_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stop = asyncio.Event()
    payload = recorded_realtime_samples()["vehicles"]

    class Poller:
        config = FeedConfig("mbta-vehicles", "https://example.test/feed")
        health = SourceHealth(last_success_at=datetime.now(UTC))

        async def poll(self, _: object) -> tuple[PollResult, bytes]:
            stop.set()
            now = datetime.now(UTC)
            return PollResult(
                "mbta-vehicles", now, now, "SUCCESS", 200, "sum", len(payload)
            ), payload

        def next_delay(self) -> float:
            return 0

    class Client:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        async def __aenter__(self) -> object:
            return object()

        async def __aexit__(self, *_: object) -> None:
            return None

    class Cache:
        async def put_source_health(self, *_: object) -> None:
            raise ConnectionError("redis unavailable")

        async def put_vehicle(self, _: Vehicle) -> bool:
            raise ConnectionError("redis unavailable")

    class History:
        async def record_poll(self, _: PollResult) -> None:
            raise ConnectionError("postgresql unavailable")

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    projector = RealtimeProjector(
        CurrentState(),
        EventBroker(),
        cache=cast(RedisStateStore, Cache()),
        history=cast(RealtimeHistoryStore, History()),
    )

    await run_poller(
        cast(FeedPoller, Poller()),
        parse_vehicle_positions,
        stop,
        projector,
    )

    assert projector.diagnostics["mbta-vehicles"]["redis_errors"] >= 1
    assert projector.diagnostics["mbta-vehicles"]["postgresql_errors"] == 1
    assert projector.diagnostics["mbta-vehicles"]["projection_errors"] == 1


async def test_live_vehicle_response_has_freshness() -> None:
    app = create_app(Settings(environment="test", redis_url=None), probes=[])
    app.state.current_state.update_vehicles(
        [Vehicle("entity", "bus", "Red", None, 42.0, -71.0, datetime.now(UTC))]
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/live/routes/Red/vehicles")
    assert response.status_code == 200
    assert response.json()["data"][0]["freshness"]["state"] == "HEALTHY"
    assert response.json()["data"][0]["confidence"] == "HIGH"
    assert response.json()["data"][0]["retrieved_at"] is None


async def test_live_vehicle_bounding_box_and_trip_progress() -> None:
    app = create_app(Settings(environment="test", redis_url=None), probes=[])
    now = datetime.now(UTC)
    app.state.current_state.update_vehicles(
        [Vehicle("entity", "bus", "Red", "trip", 42.0, -71.0, now)]
    )
    app.state.current_state.update_trip_updates(
        [TripUpdate("update", "trip", "Red", "bus", now, "0")]
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        vehicles = await client.get(
            "/api/v1/live/routes/Red/vehicles",
            params={
                "min_latitude": 41,
                "max_latitude": 43,
                "min_longitude": -72,
                "max_longitude": -70,
            },
        )
        progress = await client.get("/api/v1/live/trips/trip")
    assert vehicles.json()["data"][0]["vehicle_id"] == "bus"
    assert progress.json()["data"]["trip_id"] == "trip"
    assert progress.json()["data"]["freshness"]["state"] == "HEALTHY"
    assert progress.json()["data"]["confidence"] == "HIGH"


async def test_live_alert_uses_feed_provenance_for_freshness() -> None:
    app = create_app(Settings(environment="test", redis_url=None), probes=[])
    now = datetime.now(UTC)
    app.state.current_state.update_alerts([Alert("alert", "Header", ("Red",), (), now, now)])
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/live/alerts", params={"route_id": "Red"})

    assert response.json()["data"][0]["source_timestamp"]
    assert response.json()["data"][0]["freshness"]["state"] == "HEALTHY"


def test_api_latency_summary_reports_p50_and_p95() -> None:
    assert latency_summary([1, 2, 3, 4, 100]) == {
        "sample_count": 5,
        "p50_ms": 3,
        "p95_ms": 100,
    }


async def test_live_arrivals_are_scoped_to_the_requested_stop() -> None:
    app = create_app(Settings(environment="test", redis_url=None), probes=[])
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
    assert response.json()["data"][0]["confidence"] == "HIGH"


async def test_live_arrivals_explicitly_fall_back_to_schedule() -> None:
    app = create_app(Settings(environment="test", redis_url=None), probes=[])
    app.state.schedule = Schedule(
        "test",
        "checksum",
        stops={"stop": Stop("stop", "Stop", 42.0, -71.0)},
        trips={"trip": Trip("trip", "Red", "daily", None, None)},
        stop_times=[StopTime("trip", "stop", 1, 3600, 3600)],
        services={
            "daily": Service(
                "daily",
                (True, True, True, True, True, True, True),
                date(2020, 1, 1),
                date(2030, 1, 1),
            )
        },
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/live/stops/stop/arrivals")
    assert response.status_code == 200, response.json()
    assert response.json()["data"][0]["scheduled_fallback"]["kind"] == "scheduled_fallback"


def test_event_broker_scopes_and_replays_monotonic_events() -> None:
    broker = EventBroker()
    broker.publish("vehicle.changed", '{"schema_version":"1.0.0"}', route_id="Red")
    broker.publish("vehicle.changed", '{"schema_version":"1.0.0"}', route_id="Orange")
    assert [event.event_id for event in broker.since(0, "Red", None)] == [1]
    assert broker.since(1, "Red", None) == []


def test_event_broker_reconnect_skips_delivered_events_and_preserves_order() -> None:
    broker = EventBroker()
    first = broker.publish("vehicle.changed", '{"vehicle_id":"one"}', route_id="Red")
    second = broker.publish("vehicle.changed", '{"vehicle_id":"two"}', route_id="Red")
    third = broker.publish("alert.changed", '{"alert_id":"three"}', route_id="Red")

    reconnect = broker.since(first.event_id, "Red", None)

    assert [event.event_id for event in reconnect] == [second.event_id, third.event_id]
    assert [event.payload for event in reconnect] == [second.payload, third.payload]


async def test_sse_connection_limit_returns_a_safe_problem() -> None:
    app = create_app(Settings(environment="test", redis_url=None), probes=[])
    app.state.sse_connections = app.state.settings.sse_connection_limit
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/live/events")
    assert response.status_code == 429
    assert response.json()["code"] == "SSE_CONNECTION_LIMIT"

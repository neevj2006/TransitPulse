from datetime import UTC, datetime
from pathlib import Path

import pytest

from transitpulse.events import EventBroker
from transitpulse.history import expired_partition_names
from transitpulse.realtime import CurrentState, Vehicle
from transitpulse.worker import RealtimeProjector, build_pollers


def test_expired_partition_names_only_select_completed_months() -> None:
    before = datetime(2026, 7, 15, tzinfo=UTC)
    assert expired_partition_names(
        ["vehicle_observations_2026_06", "vehicle_observations_2026_07", "not-a-partition"],
        before,
    ) == ["vehicle_observations_2026_06"]


def test_worker_configures_independent_mbta_sources(tmp_path: Path) -> None:
    pollers = build_pollers(
        tmp_path, "https://test/vehicles", "https://test/trips", "https://test/alerts"
    )
    assert set(pollers) == {"mbta-vehicles", "mbta-trip-updates", "mbta-alerts"}
    assert {poller.config.interval_seconds for poller in pollers.values()} == {60}


@pytest.mark.asyncio
async def test_projector_updates_current_state_and_emits_route_scoped_event() -> None:
    state = CurrentState()
    broker = EventBroker()
    projector = RealtimeProjector(state, broker)
    await projector.project(
        "mbta-vehicles",
        [Vehicle("entity", "vehicle", "Red", None, 42.0, -71.0, datetime.now(UTC))],
    )
    assert state.route_vehicles("Red")[0].vehicle_id == "vehicle"
    assert broker.since(0, "Red", None)[0].kind == "vehicle.changed"


@pytest.mark.asyncio
async def test_projector_publishes_vehicle_events_to_shared_cache() -> None:
    class Cache:
        def __init__(self) -> None:
            self.events: list[tuple[str, str, str | None]] = []

        async def put_vehicle(self, _: Vehicle) -> bool:
            return True

        async def publish_event(self, kind: str, payload: str, route_id: str | None) -> None:
            self.events.append((kind, payload, route_id))

    cache = Cache()
    projector = RealtimeProjector(CurrentState(), EventBroker(), cache)  # type: ignore[arg-type]
    await projector.project(
        "mbta-vehicles",
        [Vehicle("entity", "vehicle", "Red", None, 42.0, -71.0, datetime.now(UTC))],
    )
    assert cache.events[0][0] == "vehicle.changed"
    assert cache.events[0][2] == "Red"

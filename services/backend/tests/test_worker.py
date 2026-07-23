from datetime import UTC, datetime
from pathlib import Path

import pytest

from transitpulse.events import EventBroker
from transitpulse.realtime import CurrentState, Vehicle
from transitpulse.worker import RealtimeProjector, build_pollers


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

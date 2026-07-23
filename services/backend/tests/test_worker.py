from pathlib import Path

from transitpulse.worker import build_pollers


def test_worker_configures_independent_mbta_sources(tmp_path: Path) -> None:
    pollers = build_pollers(
        tmp_path, "https://test/vehicles", "https://test/trips", "https://test/alerts"
    )
    assert set(pollers) == {"mbta-vehicles", "mbta-trip-updates", "mbta-alerts"}
    assert {poller.config.interval_seconds for poller in pollers.values()} == {60}

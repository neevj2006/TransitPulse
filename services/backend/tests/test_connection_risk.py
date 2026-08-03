from datetime import UTC, datetime, timedelta

from transitpulse.connection_risk import calculate_connection_risk


def test_connection_risk_matches_hand_calculated_pairs() -> None:
    result = calculate_connection_risk(
        planned_arrival=datetime(2026, 8, 1, 10, tzinfo=UTC),
        planned_departure=datetime(2026, 8, 1, 10, 10, tzinfo=UTC),
        walking_seconds=300,
        arrival_delays=[0] * 19 + [600],
        departure_delays=[0] * 20,
    )
    assert result.planned_buffer_seconds == 300
    assert result.missed_transfer_probability == 0.05
    assert result.risk_band == "LOW"
    assert result.sufficient_data is True


def test_connection_risk_never_invents_probability_for_short_history() -> None:
    instant = datetime(2026, 8, 1, tzinfo=UTC)
    result = calculate_connection_risk(
        planned_arrival=instant,
        planned_departure=instant + timedelta(minutes=10),
        walking_seconds=180,
        arrival_delays=[0] * 20,
        departure_delays=[0] * 19,
    )
    assert result.sufficient_data is False
    assert result.missed_transfer_probability is None
    assert result.risk_band == "UNKNOWN"

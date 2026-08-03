from transitpulse.reliability import (
    MINIMUM_COVERAGE,
    MINIMUM_SAMPLE_SIZE,
    on_time_threshold_seconds,
    percentile,
    summarize_delays,
)


def test_percentiles_use_documented_nearest_rank_method() -> None:
    values = [0, 10, 20, 30]
    assert percentile(values, 0.75) == 20
    assert percentile(values, 0.95) == 30


def test_reliability_summary_matches_hand_calculated_fixture() -> None:
    delays = [*range(MINIMUM_SAMPLE_SIZE - 1), 600]
    summary = summarize_delays(delays, MINIMUM_SAMPLE_SIZE, route_type=1)

    assert summary.sample_size == MINIMUM_SAMPLE_SIZE
    assert summary.coverage == 1
    assert summary.median_delay_seconds == 9.5
    assert summary.p75_delay_seconds == 14
    assert summary.p90_delay_seconds == 17
    assert summary.p95_delay_seconds == 18
    assert summary.on_time_percentage == 0.95
    assert summary.sufficient_data is True


def test_summary_with_missing_values_reports_insufficient_coverage() -> None:
    summary = summarize_delays([0] * 10, MINIMUM_SAMPLE_SIZE, route_type=3)

    assert summary.coverage < MINIMUM_COVERAGE
    assert summary.sufficient_data is False
    assert on_time_threshold_seconds(2) == 360
    assert on_time_threshold_seconds(3) == 300

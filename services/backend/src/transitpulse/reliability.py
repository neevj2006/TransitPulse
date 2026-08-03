"""Versioned, explainable reliability metric definitions."""

from collections.abc import Iterable
from dataclasses import dataclass
from math import ceil
from statistics import median

METRIC_VERSION = "2026-08-03.1"
MINIMUM_SAMPLE_SIZE = 20
MINIMUM_COVERAGE = 0.8


@dataclass(frozen=True)
class ReliabilitySummary:
    sample_size: int
    coverage: float
    median_delay_seconds: float | None
    p75_delay_seconds: float | None
    p90_delay_seconds: float | None
    p95_delay_seconds: float | None
    on_time_percentage: float | None
    sufficient_data: bool


def on_time_threshold_seconds(route_type: int | None) -> int:
    """Return the published late threshold; early arrivals are not penalized."""
    # MBTA subway (0/1/2) and bus (3/11) both use a rider-meaningful five-minute
    # late threshold in this baseline. Rail/ferry use six minutes for sparse service.
    return 360 if route_type in {2, 4, 5, 6, 7, 12} else 300


def percentile(values: list[int], fraction: float) -> float | None:
    """Nearest-rank percentile, chosen to remain reproducible across databases."""
    if not values:
        return None
    ordered = sorted(values)
    return float(ordered[max(0, ceil(fraction * len(ordered)) - 1)])


def summarize_delays(
    delays: Iterable[int | None], expected_observations: int, route_type: int | None
) -> ReliabilitySummary:
    """Summarize observed stop-prediction delay without implying missing trips."""
    observed = sorted(value for value in delays if value is not None)
    sample_size = len(observed)
    coverage = sample_size / expected_observations if expected_observations else 0.0
    sufficient = sample_size >= MINIMUM_SAMPLE_SIZE and coverage >= MINIMUM_COVERAGE
    threshold = on_time_threshold_seconds(route_type)
    return ReliabilitySummary(
        sample_size=sample_size,
        coverage=coverage,
        median_delay_seconds=float(median(observed)) if observed else None,
        p75_delay_seconds=percentile(observed, 0.75),
        p90_delay_seconds=percentile(observed, 0.90),
        p95_delay_seconds=percentile(observed, 0.95),
        on_time_percentage=(sum(value <= threshold for value in observed) / sample_size)
        if observed
        else None,
        sufficient_data=sufficient,
    )

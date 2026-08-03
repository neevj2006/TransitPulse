"""Deterministic, evidence-labelled transfer-risk baseline."""

from dataclasses import dataclass
from datetime import datetime

CALCULATION_VERSION = "2026-08-03.1"
MINIMUM_CONNECTION_SAMPLES = 20
LOW_RISK_MAXIMUM = 0.15
MEDIUM_RISK_MAXIMUM = 0.35


@dataclass(frozen=True)
class ConnectionRisk:
    sufficient_data: bool
    missed_transfer_probability: float | None
    risk_band: str
    planned_buffer_seconds: int
    sample_size: int
    arrival_sample_size: int
    departure_sample_size: int
    source_first_at: datetime | None
    source_last_at: datetime | None
    assumptions: tuple[str, ...]


def risk_band(probability: float) -> str:
    if probability <= LOW_RISK_MAXIMUM:
        return "LOW"
    if probability <= MEDIUM_RISK_MAXIMUM:
        return "MEDIUM"
    return "HIGH"


def calculate_connection_risk(
    *,
    planned_arrival: datetime,
    planned_departure: datetime,
    walking_seconds: int,
    arrival_delays: list[int],
    departure_delays: list[int],
    source_first_at: datetime | None = None,
    source_last_at: datetime | None = None,
) -> ConnectionRisk:
    """Calculate an independent empirical baseline from historical delay samples.

    Every arrival/departure pair is evaluated.  This deliberately simple
    Cartesian baseline is reproducible and makes no unsupported claim that
    delays on two independently selected trips are causally linked.
    """
    buffer_seconds = int((planned_departure - planned_arrival).total_seconds()) - walking_seconds
    assumptions = (
        "Historical arrival and departure delays are paired independently.",
        "Walking time is a fixed input; platform congestion and accessibility "
        "needs are not modelled.",
    )
    if (
        len(arrival_delays) < MINIMUM_CONNECTION_SAMPLES
        or len(departure_delays) < MINIMUM_CONNECTION_SAMPLES
    ):
        return ConnectionRisk(
            sufficient_data=False,
            missed_transfer_probability=None,
            risk_band="UNKNOWN",
            planned_buffer_seconds=buffer_seconds,
            sample_size=min(len(arrival_delays), len(departure_delays)),
            arrival_sample_size=len(arrival_delays),
            departure_sample_size=len(departure_delays),
            source_first_at=source_first_at,
            source_last_at=source_last_at,
            assumptions=(
                *assumptions,
                "A probability requires at least 20 observations for both legs.",
            ),
        )
    combinations = len(arrival_delays) * len(departure_delays)
    missed = sum(
        arrival_delay + walking_seconds
        > (planned_departure - planned_arrival).total_seconds() + departure_delay
        for arrival_delay in arrival_delays
        for departure_delay in departure_delays
    )
    probability = missed / combinations
    return ConnectionRisk(
        sufficient_data=True,
        missed_transfer_probability=probability,
        risk_band=risk_band(probability),
        planned_buffer_seconds=buffer_seconds,
        sample_size=min(len(arrival_delays), len(departure_delays)),
        arrival_sample_size=len(arrival_delays),
        departure_sample_size=len(departure_delays),
        source_first_at=source_first_at,
        source_last_at=source_last_at,
        assumptions=assumptions,
    )

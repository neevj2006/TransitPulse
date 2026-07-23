from dataclasses import dataclass
from datetime import UTC, datetime
from math import asin, cos, radians, sin, sqrt

from transitpulse.polling import PollResult, SourceHealth
from transitpulse.realtime import Vehicle


@dataclass(frozen=True)
class FeedDiagnostic:
    source_id: str
    state: str
    source_age_seconds: int | None
    success_rate: float
    consecutive_failures: int


def summarize(
    source_id: str, health: SourceHealth, history: list[PollResult], now: datetime | None = None
) -> FeedDiagnostic:
    moment = now or datetime.now(UTC)
    successful = sum(item.outcome in {"SUCCESS", "NOT_MODIFIED"} for item in history)
    age = int((moment - health.last_success_at).total_seconds()) if health.last_success_at else None
    return FeedDiagnostic(
        source_id,
        health.state(moment),
        age,
        successful / len(history) if history else 0.0,
        health.failures,
    )


def vehicle_quality(previous: Vehicle, current: Vehicle, frozen_seconds: int = 300) -> set[str]:
    """Return diagnostic signals; these are not agency-confirmed incidents."""
    signals: set[str] = set()
    if not previous.source_timestamp or not current.source_timestamp:
        return signals
    elapsed = (current.source_timestamp - previous.source_timestamp).total_seconds()
    if elapsed <= 0:
        return {"TIMESTAMP_REGRESSION"}
    if (
        previous.latitude == current.latitude
        and previous.longitude == current.longitude
        and elapsed >= frozen_seconds
    ):
        signals.add("VEHICLE_FROZEN")
    phi1, phi2 = radians(previous.latitude), radians(current.latitude)
    delta_phi, delta_lambda = (
        radians(current.latitude - previous.latitude),
        radians(current.longitude - previous.longitude),
    )
    a = sin(delta_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(delta_lambda / 2) ** 2
    meters = 6_371_000 * 2 * asin(sqrt(a))
    if meters / elapsed > 55:
        signals.add("VEHICLE_IMPOSSIBLE_JUMP")
    return signals

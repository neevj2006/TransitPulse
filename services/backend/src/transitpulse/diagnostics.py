from dataclasses import dataclass
from datetime import UTC, datetime

from transitpulse.polling import PollResult, SourceHealth


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

import json
from pathlib import Path

import pytest

from transitpulse.replay import replay_frames
from transitpulse.soak import summarize


def test_recorded_replay_preserves_provenance_and_relative_timing() -> None:
    path = Path(__file__).resolve().parents[3] / "data/fixtures/realtime/mbta-recorded-samples.json"
    sample = json.loads(path.read_text(encoding="utf-8"))
    later = {**sample, "recorded_at": "2023-11-14T22:14:20Z"}
    frames = replay_frames([later, sample], 10)
    assert frames[0]["playback_offset_seconds"] == 0
    assert frames[1]["playback_offset_seconds"] == 6
    assert frames[0]["recorded_at"] == sample["recorded_at"]
    assert frames[0]["vehicles"][0]["vehicle_id"] == "v-recorded"
    assert frames == replay_frames([later, sample], 10)


def test_replay_rejects_invalid_speed() -> None:
    with pytest.raises(ValueError):
        replay_frames([], 0)


def test_soak_report_never_treats_short_runs_as_long_duration_validation() -> None:
    result = summarize([{"ok": True, "latency_ms": 25}, {"ok": False, "latency_ms": 50}], 60)
    assert result["availability"] == 0.5
    assert result["api_p95_ms"] == 25
    assert result["completed_24_hours"] is False
    assert result["completed_seven_days"] is False

"""Replay public fixture captures without publishing them into live state."""

import argparse
import base64
import io
import json
import time
import zipfile
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from transitpulse.realtime import parse_alerts, parse_trip_updates, parse_vehicle_positions
from transitpulse.schedule.importer import import_archive


def replay_frames(captures: list[dict[str, Any]], speed: float) -> list[dict[str, Any]]:
    if not 0 < speed <= 100:
        raise ValueError("Replay speed must be greater than zero and at most 100")
    ordered = sorted(captures, key=lambda value: value["recorded_at"])
    frames: list[dict[str, Any]] = []
    first = datetime.fromisoformat(ordered[0]["recorded_at"]) if ordered else None
    for capture in ordered:
        moment = datetime.fromisoformat(capture["recorded_at"])
        if not moment.tzinfo or not first or not first.tzinfo:
            raise ValueError("Capture timestamps must include a time zone")
        samples = capture["samples"]
        frames.append(
            {
                "mode": "recorded-demonstration",
                "recorded_at": capture["recorded_at"],
                "playback_offset_seconds": (moment - first).total_seconds() / speed,
                "vehicles": [
                    asdict(value)
                    for value in parse_vehicle_positions(base64.b64decode(samples["vehicles"]))
                ],
                "trip_updates": [
                    asdict(value)
                    for value in parse_trip_updates(base64.b64decode(samples["trip_updates"]))
                ],
                "alerts": [
                    asdict(value) for value in parse_alerts(base64.b64decode(samples["alerts"]))
                ],
            }
        )
    return frames


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=Path("../../data/fixtures"))
    parser.add_argument("--speed", type=float, default=1)
    args = parser.parse_args()
    root: Path = args.fixtures
    cases = json.loads((root / "gtfs/archive-cases.json").read_text(encoding="utf-8"))
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as target:
        for name, content in cases["safe"].items():
            target.writestr(name, content)
    schedule = import_archive(archive.getvalue())
    print(json.dumps({"mode": "recorded-demonstration", "schedule": schedule.import_statistics()}))
    sample = json.loads((root / "realtime/mbta-recorded-samples.json").read_text(encoding="utf-8"))
    captures = cast(list[dict[str, Any]], sample if isinstance(sample, list) else [sample])
    started = time.monotonic()
    for frame in replay_frames(captures, args.speed):
        time.sleep(max(0, frame["playback_offset_seconds"] - (time.monotonic() - started)))
        print(json.dumps(frame, default=str), flush=True)


if __name__ == "__main__":
    main()

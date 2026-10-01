"""Collect bounded health evidence; elapsed validation time is never simulated."""

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from typing import Any

import httpx


def summarize(samples: list[dict[str, Any]], elapsed: float) -> dict[str, Any]:
    latencies = sorted(float(item["latency_ms"]) for item in samples if item["ok"])
    return {
        "elapsed_seconds": elapsed,
        "sample_count": len(samples),
        "successful_samples": len(latencies),
        "availability": len(latencies) / len(samples) if samples else None,
        "api_p95_ms": latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))]
        if latencies
        else None,
        "completed_24_hours": elapsed >= 86400,
        "completed_seven_days": elapsed >= 604800,
    }


async def collect(origin: str, hours: float, interval: float, output: Path) -> None:
    if not 0 < hours <= 744 or not 5 <= interval <= 3600:
        raise ValueError("Use 0-744 hours and a 5-3600 second interval")
    output.parent.mkdir(parents=True, exist_ok=True)
    started = monotonic()
    samples: list[dict[str, Any]] = []
    async with httpx.AsyncClient(base_url=origin, timeout=15) as client:
        try:
            while monotonic() - started < hours * 3600:
                tick = monotonic()
                item: dict[str, Any] = {"at": datetime.now(UTC).isoformat(), "ok": False}
                try:
                    response = await client.get("/api/v1/live/health")
                    item["ok"] = response.is_success
                    item["status"] = response.status_code
                    if response.is_success:
                        payload = response.json()
                        item["sources"] = payload.get("data", [])
                        item["measurements"] = payload.get("meta", {})
                except httpx.HTTPError:
                    item["error"] = "REQUEST_FAILED"
                item["latency_ms"] = round((monotonic() - tick) * 1000, 3)
                samples.append({"ok": item["ok"], "latency_ms": item["latency_ms"]})
                with output.open("a", encoding="utf-8") as target:
                    target.write(json.dumps(item) + "\n")
                await asyncio.sleep(min(interval, max(0, hours * 3600 - (monotonic() - started))))
        finally:
            summary = summarize(samples, monotonic() - started)
            output.with_suffix(".summary.json").write_text(
                json.dumps(summary, indent=2) + "\n", encoding="utf-8"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", default="http://127.0.0.1:8000")
    parser.add_argument("--hours", type=float, default=24)
    parser.add_argument("--interval", type=float, default=60)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(collect(args.origin, args.hours, args.interval, args.output))


if __name__ == "__main__":
    main()

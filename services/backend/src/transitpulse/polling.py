"""Bounded, independently schedulable GTFS-Realtime polling primitives."""

import asyncio
import gzip
import hashlib
import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx


@dataclass(frozen=True)
class FeedConfig:
    source_id: str
    url: str
    interval_seconds: int = 60
    timeout_seconds: float = 15
    maximum_bytes: int = 25 * 1024 * 1024


@dataclass(frozen=True)
class PollResult:
    source_id: str
    started_at: datetime
    completed_at: datetime
    outcome: str
    status_code: int | None
    checksum: str | None
    bytes_received: int
    error_code: str | None = None


@dataclass
class SourceHealth:
    failures: int = 0
    last_success_at: datetime | None = None
    circuit_open_until: datetime | None = None
    etag: str | None = None
    last_modified: str | None = None

    def state(self, now: datetime) -> str:
        if self.circuit_open_until and self.circuit_open_until > now:
            return "OFFLINE"
        if self.last_success_at is None:
            return "UNKNOWN"
        return "HEALTHY" if (now - self.last_success_at).total_seconds() <= 90 else "STALE"


class RawSnapshotStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def save(self, source_id: str, payload: bytes, retrieved_at: datetime) -> str:
        checksum = hashlib.sha256(payload).hexdigest()
        folder = self.root / source_id / retrieved_at.strftime("%Y%m%d%H")
        destination = folder / f"{checksum}.pb.gz"
        if not destination.exists():
            folder.mkdir(parents=True, exist_ok=True)
            with gzip.open(destination, "wb") as target:
                target.write(payload)
        return checksum

    def prune(self, before: datetime) -> int:
        removed = 0
        paths: list[Path] = list(self.root.rglob("*.pb.gz")) if self.root.exists() else []
        for path in paths:
            if datetime.fromtimestamp(path.stat().st_mtime, UTC) < before:
                path.unlink()
                removed += 1
        return removed


class FeedPoller:
    def __init__(self, config: FeedConfig, raw_store: RawSnapshotStore) -> None:
        self.config, self.raw_store = config, raw_store
        self.health = SourceHealth()
        self._lock = asyncio.Lock()

    async def poll(self, client: httpx.AsyncClient) -> tuple[PollResult, bytes | None]:
        async with self._lock:
            started_at = datetime.now(UTC)
            if self.health.circuit_open_until and self.health.circuit_open_until > started_at:
                return PollResult(
                    self.config.source_id,
                    started_at,
                    started_at,
                    "CIRCUIT_OPEN",
                    None,
                    None,
                    0,
                    "SOURCE_OFFLINE",
                ), None
            headers = {"User-Agent": "TransitPulse/0.1 (https://github.com/neevj2006/TransitPulse)"}
            if self.health.etag:
                headers["If-None-Match"] = self.health.etag
            if self.health.last_modified:
                headers["If-Modified-Since"] = self.health.last_modified
            try:
                async with client.stream(
                    "GET", self.config.url, headers=headers, timeout=self.config.timeout_seconds
                ) as response:
                    if response.status_code == 304:
                        return PollResult(
                            self.config.source_id,
                            started_at,
                            datetime.now(UTC),
                            "NOT_MODIFIED",
                            304,
                            None,
                            0,
                        ), None
                    response.raise_for_status()
                    chunks: list[bytes] = []
                    total = 0
                    async for chunk in response.aiter_bytes():
                        total += len(chunk)
                        if total > self.config.maximum_bytes:
                            raise ValueError("PAYLOAD_TOO_LARGE")
                        chunks.append(chunk)
                    payload = b"".join(chunks)
                    self.health.etag = response.headers.get("etag")
                    self.health.last_modified = response.headers.get("last-modified")
            except (httpx.HTTPError, ValueError) as error:
                self.health.failures += 1
                if self.health.failures >= 3:
                    cooldown_seconds = min(300, 2 ** min(self.health.failures, 8))
                    self.health.circuit_open_until = datetime.now(UTC) + timedelta(
                        seconds=cooldown_seconds
                    )
                return PollResult(
                    self.config.source_id,
                    started_at,
                    datetime.now(UTC),
                    "ERROR",
                    None,
                    None,
                    0,
                    "PAYLOAD_TOO_LARGE"
                    if str(error) == "PAYLOAD_TOO_LARGE"
                    else "SOURCE_HTTP_ERROR",
                ), None
            checksum = self.raw_store.save(self.config.source_id, payload, datetime.now(UTC))
            self.health.failures, self.health.last_success_at, self.health.circuit_open_until = (
                0,
                datetime.now(UTC),
                None,
            )
            return PollResult(
                self.config.source_id,
                started_at,
                datetime.now(UTC),
                "SUCCESS",
                200,
                checksum,
                len(payload),
            ), payload

    def next_delay(self) -> float:
        return self.config.interval_seconds + random.uniform(
            0, min(5, self.config.interval_seconds * 0.1)
        )

# TransitPulse backend

The backend provides versioned static GTFS ingestion and scheduled APIs,
GTFS-Realtime polling and normalization, selected historical evidence, Valkey
current-state projections, feed diagnostics, and Server-Sent Events.

## Setup

From this directory:

```sh
uv sync --frozen
```

Copy `.env.example` to `.env` and replace every placeholder before connecting to
local services.

## Commands

```sh
uv run transitpulse-api
uv run transitpulse-worker
uv run transitpulse-migrate
uv run transitpulse-import-gtfs
uv run pytest
uv run ruff format --check .
uv run ruff check .
uv run pyright
```

The API listens on `127.0.0.1:8000` by default. Operational endpoints include:

- `GET /health/live`
- `GET /health/ready`
- `GET /version`
- `GET /api/v1/live/health`
- `GET /api/v1/live/events`

Scheduled routes, stops, shapes, nearby stops, search, and arrivals are exposed
under `/api/v1`. Live vehicles, trip progress, stop arrivals, and alerts are
under `/api/v1/live`. Interactive schemas are available at `/docs`.

Readiness returns HTTP 503 until PostgreSQL and Valkey are configured and
reachable.

Integration tests use `TP_DATABASE_URL` and `TP_REDIS_URL`. Without them, the
dependency tests skip while all offline parser, contract, and failure tests still
run.

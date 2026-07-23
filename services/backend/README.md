# TransitPulse backend

The backend foundation provides a FastAPI application, database and cache
readiness probes, structured logging, Alembic migrations, and a worker command.

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
uv run pytest
uv run ruff format --check .
uv run ruff check .
uv run pyright
```

The API listens on `127.0.0.1:8000` by default. Its foundation endpoints are:

- `GET /health/live`
- `GET /health/ready`
- `GET /version`

Readiness returns HTTP 503 until PostgreSQL and Valkey are configured and
reachable.

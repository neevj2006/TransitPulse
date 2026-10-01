# Testing and reproducibility

Use Node.js 22, pnpm 11, Python 3.12, uv, and Docker. Install locked dependencies before running checks.

```sh
pnpm install --frozen-lockfile
pnpm format
pnpm --filter web lint
pnpm --filter web typecheck
pnpm --filter web test
pnpm --filter web build
pnpm --filter web exec playwright install chromium
pnpm --filter web test:e2e
cd services/backend
uv sync --frozen
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest -m "not integration"
```

The Chromium suite exercises search to arrival boards, vehicle selection, alert filtering, transfer calculation, demonstration outages, empty filters, keyboard navigation, 320/768/1440px layouts, themes, PWA metadata, accessibility checks, and browser errors. The demo scenario uses the actual Next.js fixture endpoints without mocked network responses.

Integration tests need `TP_DATABASE_URL` and `TP_REDIS_URL` pointing to disposable local services. Start [local infrastructure](../infra/README.md), apply `uv run alembic upgrade head`, run `uv run alembic check`, then `uv run pytest -m integration`. Do not run test mutations against production data.

Offline static and realtime fixture tests cover archive/parser boundaries, service dates, reconciliation, TTL expiry, and scheduled fallback. The recorded replay CLI exercises these same parsers:

```sh
uv run transitpulse-replay --speed 10
```

The checked-in capture is a small compatible fixture, not a long historical dataset. Multi-capture input preserves source timestamps and scales relative playback timing. CLI replay never writes demonstration observations into live state.

## Long-duration evidence

Run the collector against a continuously running live stack:

```sh
uv run transitpulse-soak --hours 24 --output /private/validation/day.jsonl
uv run transitpulse-soak --hours 168 --output /private/validation/week.jsonl
```

Choose a private local output path appropriate to your operating system. Each sample retains source diagnostics and latency. The summary uses actual elapsed time and explicitly distinguishes short checks from completed 24-hour and seven-day runs. API availability does not prove source freshness: inspect per-source health as well. Retention, database size, backup recovery, and browser delivery timing require their own observations. A successful short test cannot establish an uptime or storage-growth claim.

# TransitPulse

TransitPulse is an open-source foundation for working with scheduled and
realtime public-transit data.

The repository is being built incrementally. Its current foundation includes a
Next.js health interface, a FastAPI service, and local PostGIS and Valkey
infrastructure.

## Repository layout

- `apps/web` — web application
- `services/backend` — API and background services
- `data/fixtures` — deterministic test fixtures
- `infra` — local development infrastructure
- `docs` — public technical documentation

## License

TransitPulse is available under the [MIT License](LICENSE).

## Prerequisites

- Node.js 22 and pnpm 11
- Python 3.12 and uv
- Docker with Docker Compose

## Local setup

1. Install frontend dependencies with `pnpm install --frozen-lockfile`.
2. In `services/backend`, run `uv sync --frozen`.
3. Follow the [local infrastructure setup](infra/README.md).
4. Start the backend with `uv run transitpulse-api`.
5. From the repository root, start the frontend with `pnpm --filter web dev`.

The frontend is available at `http://localhost:3000/health`; backend health is
available at `http://127.0.0.1:8000/health/live`.

Environment examples contain placeholders or non-secret public defaults only.
Local `.env` files are ignored. Development, preview, and production
environments must use separate values and credentials.

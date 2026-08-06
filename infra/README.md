# Local infrastructure

Docker Compose provides PostgreSQL 17 with PostGIS and Valkey for development.
Both services use named volumes and report health before dependent processes are
started.

## First start

1. Copy `infra/.env.example` to `infra/.env`.
2. Replace every `replace_with_...` value with local-only credentials.
3. Start the services:

   ```sh
   docker compose --env-file infra/.env -f infra/compose.yaml up -d --wait
   ```

4. Set the backend environment:

   ```text
   TP_DATABASE_URL=postgresql+asyncpg://<user>:<password>@localhost:55432/<database>
   TP_REDIS_URL=redis://localhost:56379/0
   ```

5. Apply migrations:

   ```sh
   cd services/backend
   uv run alembic upgrade head
   ```

6. Start the API with `uv run transitpulse-api`.

Inspect service health with:

```sh
docker compose --env-file infra/.env -f infra/compose.yaml ps
```

Stop containers with `docker compose --env-file infra/.env -f
infra/compose.yaml down`. Named volumes remain intact. Add `--volumes` only when
you intentionally want to remove local database and cache data.

## Raw snapshots

The optional raw-snapshot path defaults to `data/raw`. Its contents are ignored
by Git; only the directory marker is public. Future ingestion commands may
override the path through `TP_RAW_SNAPSHOT_PATH`.

## Self-hosted production stack

`compose.production.yaml` runs the API, worker, PostgreSQL/PostGIS, Valkey,
frontend, and Caddy on one host. PostgreSQL and Valkey are private to the Docker
network; Caddy is the only service that publishes ports and obtains HTTPS
certificates. The containers run as non-root users where their upstream images
support it.

1. Point `PUBLIC_HOSTNAME` at the host and allow inbound TCP 80 and 443.
2. Copy `infra/.env.example` to a host-local `infra/.env`, replacing the
   placeholder database password and production host values.
3. Build and start the stack:

   ```sh
   docker compose --env-file infra/.env -f infra/compose.production.yaml up --build -d --wait
   ```

4. Inspect readiness through the public hostname and keep the generated Caddy
   volumes and database volumes in the documented backup scope.

The migration container exits after a successful upgrade. Compose will not start
the API or worker if migration fails. Stop the stack with `docker compose
--env-file infra/.env -f infra/compose.production.yaml down`; do not append
`--volumes` unless intentionally deleting persistent production data.

For a host-only smoke test, set `PUBLIC_HOSTNAME=localhost`,
`HTTP_PORT=8080`, and `HTTPS_PORT=8443` before starting the stack. Caddy uses a
locally trusted development certificate in that configuration; use `curl -k` for
the short-lived smoke test only. Do not use those values for a public deployment.

## Reliability aggregation

Run `uv run transitpulse-aggregate-reliability` after applying migrations. It
atomically replaces the selected metric version from retained trip-update
evidence and retains a safe job audit record. The checked-in
`infra/reliability-aggregation.cron` is a zero-cost daily scheduler template;
install it only after replacing its placeholder project path and supplying the
database URL through the scheduler environment. Re-run the command after a
metric-definition version change to rebuild that version without mixing results.

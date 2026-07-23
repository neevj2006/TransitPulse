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

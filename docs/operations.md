# Operations and recovery

## Metrics and logs

The backend exposes Prometheus text metrics at `/metrics`. Scrape it only on the
private service network: it exposes request paths and operational volumes, not a
public rider API. Worker JSON logs include `source_id`, outcome, payload bytes,
poll duration, parser/projection errors, and feed age. API logs include the
request ID returned in `X-Request-ID`, method, path, status, and duration.

Do not log request headers, database URLs, feed credentials, access tokens, or
raw payloads. The structured logger redacts common credential field names. Retain
production application logs for 14 days and restrict access to operators.

Use the operator feed-health route for poll success, parser/reconciliation
diagnostics, current feed age, Redis telemetry, and API latency. Alert when a
source is stale for more than 90 seconds, when poll failures reach the circuit
breaker threshold, or when the 5xx rate rises above 1% for five minutes.

## Failure behaviour

Each source is independently polled. Three consecutive request failures open a
bounded exponential-backoff circuit; source health becomes offline, and rider
views preserve clearly-labelled scheduled fallback rather than presenting old data
as live. Payload size limits, parser failures, duplicate payload handling,
timestamp regression rejection, vehicle TTLs, and reconciliation quarantine keep
bad feed input out of current-state projections. Redis and PostgreSQL failures are
logged and surfaced through readiness/feed-health checks; a recovered dependency
is used on the next poll without a worker restart.

## Backups and restore

Run `infra/backup.ps1 -Destination <private-backup-directory>` once daily from a
host scheduler with `TP_DATABASE_URL` set in the scheduler environment. The script
uses PostgreSQL custom format, verifies every dump with `pg_restore --list`, and
keeps fourteen days. Store production backups on encrypted storage with access
limited to operators; local development backups may remain on an encrypted user
disk. Raw snapshots are short-lived troubleshooting data and are not backed up;
checked-in fixtures are source-controlled.

Restore into a clean database using `pg_restore --clean --if-exists --no-owner
--dbname <target-url> <backup.dump>`, then start the API and verify
`/health/ready`. Recovery target: restore service within four hours; recovery
point: up to the preceding daily backup. A clean-host recovery requires the
repository, ignored environment configuration, database dump, and the documented
Docker Compose startup path.

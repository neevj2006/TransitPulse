# Realtime data and trust behavior

TransitPulse polls the public MBTA Vehicle Positions, Trip Updates, and Alerts
GTFS-Realtime feeds independently. Successful payloads are stored as compressed,
checksummed raw evidence before normalization. The worker uses timeouts,
conditional requests, bounded backoff, a circuit breaker, and non-overlapping
source polls.

## Current state and freshness

Valkey holds rebuildable current vehicles, trip updates, stop predictions,
alerts, source health, and route/stop indexes with bounded TTLs. Older vehicle or
trip timestamps cannot overwrite newer values. API responses keep scheduled,
agency-predicted, and fallback values structurally distinct and attach source
time, retrieval time, age, freshness, and confidence to realtime values.

Server-Sent Events publish versioned route- and stop-scoped changes. Event IDs
support bounded replay with `Last-Event-ID`; clients fall back to 30-second
polling while SSE is unavailable.

## Static reconciliation

Realtime route, trip, stop, direction, and service-date descriptors are checked
against the active and immediately preceding static feed. Service matching uses
the explicit GTFS-Realtime start date when present; otherwise it considers the
MBTA local date and preceding service date for after-midnight trips.

Unreconciled entities are quarantined instead of guessed. Matching outcomes are
`MATCHED`, `PARTIAL`, `REALTIME_ADDED`, or `UNRECONCILED`, with confidence and
failure reasons persisted as TransitPulse quality evidence.

## History, diagnostics, and retention

Detailed vehicle and trip-update evidence is limited to Red, Orange, and Green B.
It includes delay changes, cancellations, skipped stops, feed gaps, impossible
jumps, frozen vehicles, parser failures, and reconciliation outcomes. These
diagnostics are labeled `TRANSITPULSE_INFERENCE`; they are not agency-confirmed
incidents.

Raw snapshots retain six hours. Detailed observations retain fourteen days and
use native PostgreSQL partitions. Feed health reports source age, poll success,
poll latency, parser/reconciliation rates, entity changes, API latency, and safe
Valkey usage telemetry without exposing credentials or internal exception data.

## Offline fixtures

`data/fixtures/gtfs/archive-cases.json` records safe, malformed, missing-file,
and path-traversal static archive cases. The realtime fixture manifest contains
public MBTA-compatible protobuf payloads for vehicles, trip updates, and alerts.
Tests use these files without contacting live endpoints.

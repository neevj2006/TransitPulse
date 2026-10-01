# Engineering trustworthy transit information

TransitPulse's central problem is distinguishing available data from trustworthy
data. A successful HTTP response can still contain old predictions, unmatched
trips, or no useful evidence. The rider needs those distinctions before deciding
whether to wait or attempt a connection.

## Reconciliation and time

Static GTFS supplies versioned routes, trips, stops, service calendars, and stop
times. Realtime records must reconcile against that schedule before entering
current-state projections. Unknown references are counted and quarantined rather
than silently attached to a similarly named route. An atomic schedule activation
keeps readers from observing a partially imported feed.

Service dates are distinct from calendar timestamps. GTFS times past 24:00 belong
to the preceding service day, and conversion uses the agency timezone. Tests cover
post-midnight service and daylight-saving boundaries. Prediction timestamps remain
distinct from scheduled departures and verified observations.

## Data lifetime and cost

Valkey contains disposable current state with bounded TTLs. PostgreSQL stores
versioned schedules, observations, and compact aggregates. A vehicle disappears
after its freshness lifetime; the frontend preserves labeled schedule fallback
instead of keeping an old position apparently live. The service worker excludes
API responses from its cache.

Detailed history is limited to Red, Orange, and Green B with a fourteen-day local
retention policy. Raw troubleshooting snapshots expire after six hours; compact
aggregates have a longer lifetime. Native PostgreSQL partitions make retention an
explicit maintenance operation. These are configured limits, not measured hosted
storage-growth claims.

One Python package serves separate API, polling, import, and aggregation processes.
That keeps deployment understandable while allowing the worker to restart without
restarting the API. SSE fits one-way updates, and normal HTTP remains the fallback.
Kafka, microservices, and advanced prediction models would add operational cost
without demonstrated demand at this scale.

## Evidence and limits

The release validation includes 81 backend unit tests, four database/cache
integration tests, fifteen frontend unit tests, and nine Chromium scenarios.
The browser scenarios exercise search, arrivals, degraded feeds, transfer inputs,
theme changes, responsive layouts, and console errors. Production builds and
container builds are separate checks.

Reliability uses sample counts and coverage gates. Transfer risk compares
historical arrival/departure delays with the planned buffer and walking time;
insufficient evidence stays explicit. Recorded fixtures verify deterministic
processing, while the public demonstration uses clearly labeled synthetic
examples. Neither is a substitute for chronological evaluation on retained live
data.

Long-duration uptime, real storage growth, end-to-end update latency, and deployed
API p95 remain unmeasured for this release. The soak command records elapsed wall
time and cannot turn an accelerated replay into a 24-hour or seven-day result.
See [testing](testing.md) for collection commands and [performance](performance.md)
for the separately measured local frontend audit.

## Lessons and next validation

Deployment review exposed unused frontend build arguments and proxy identity that
would combine riders into one rate-limit bucket. Explicit build arguments and a
single trusted proxy address now have regression checks. Live-stream quotas apply
per client as well as globally; metric labels and response/cache sizes are bounded.

The next evidence needed is continuous collection on the selected host, measured
retention and recovery, and chronological reliability/transfer calibration.
Production role grants and host configuration must be verified on that host.
Adding a more complex model before collecting this evidence would obscure the
existing uncertainty.

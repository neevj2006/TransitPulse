# API and data contract

The live backend publishes interactive OpenAPI documentation at `/docs` and its schema at `/openapi.json`. Responses use `schema_version`, `data`, and `meta`; errors expose a stable code, safe message, and request identifier. Dates and timestamps remain explicit, and GTFS seconds can exceed 86,400.

| Endpoint                                                   | Purpose                                         |
| ---------------------------------------------------------- | ----------------------------------------------- |
| `GET /api/v1/search?q=Harvard`                             | Labeled route, stop, and destination matches    |
| `GET /api/v1/routes`                                       | Paginated route discovery                       |
| `GET /api/v1/routes/{id}`                                  | Schedule route and trips                        |
| `GET /api/v1/routes/{id}/stops`                            | Representative stop sequence and directions     |
| `GET /api/v1/routes/{id}/shape`                            | GeoJSON route shapes                            |
| `GET /api/v1/stops/nearby?latitude=42.36&longitude=-71.06` | Nearby stops                                    |
| `GET /api/v1/stops/{id}/arrivals?service_date=2026-07-24`  | Scheduled service-day departures                |
| `GET /api/v1/live/vehicles`                                | Current bounded vehicle projection              |
| `GET /api/v1/live/stops/{id}/arrivals`                     | Predictions or explicit scheduled fallback      |
| `GET /api/v1/live/alerts`                                  | Agency service alerts                           |
| `GET /api/v1/live/events`                                  | SSE changes, optionally scoped by route or stop |
| `GET /api/v1/live/health`                                  | Public source diagnostics and recent outcomes   |
| `GET /api/v1/reliability`                                  | At most 1,000 latest route/hour aggregate rows  |
| `GET /api/v1/transfer-risk`                                | Empirical transfer baseline                     |
| `GET /health/live`, `/health/ready`                        | Process and dependency health                   |
| `GET /metrics`                                             | Local operational metric exposition             |

Reliability accepts route, direction, stop, weekday, and hour filters. Percentages in this contract are fractions unless explicitly named `*_percent`. Quantiles describe individual aggregate buckets; averaging bucket percentiles does not produce a valid overall percentile.

Transfer risk requires arriving/connecting route and stop IDs, timezone-aware planned arrival/departure timestamps, and optional walking seconds from zero to 3,600. Departure must follow arrival. The calculation uses observations before the planned journey and current time, and reports insufficient data instead of fabricating a probability. Results use a sixty-second cache bounded to 1,000 entries.

SSE clients can send a non-negative numeric `Last-Event-ID` of at most eighteen digits. Invalid cursors are rejected before consuming connection capacity. The application provides a best-effort stream, not durable client message delivery.

## Demonstration contract

When demo mode is selected, Next.js serves a bounded fixture subset under `/api/v1`. Metadata includes `mode: demonstration` and `synthetic: true`, and responses are never cached. Unknown fixture endpoints return 404. `demo_seconds` selects a reproducible playback instant; `demo_scenario` selects healthy, stale, or outage behavior. These endpoints do not proxy arbitrary URLs or contact a live backend.

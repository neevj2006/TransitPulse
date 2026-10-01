# Security boundaries and deployment assumptions

TransitPulse exposes public read-only transit information. There are no user accounts, private rider records, or privileged operator UI actions. Browser location is requested only on user action; recent searches and theme preferences stay in local browser storage.

| Boundary                      | Protected asset                              | Control and residual obligation                                                                                                                          |
| ----------------------------- | -------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Public requests to FastAPI    | Availability and data integrity              | Validated parameters, bound SQL parameters, limited result sizes, request-rate and SSE caps; deploy behind an HTTPS proxy with additional abuse controls |
| External GTFS data to parsers | Process memory, filesystem, trusted schedule | Archive/download limits, path checks, reference validation and versioned atomic imports; source operators remain trusted to configure feed destinations  |
| Feed data to browser          | Rider trust and script integrity             | React text rendering, explicit provenance, TTLs and fallback; keep frontend dependencies patched                                                         |
| API to PostgreSQL             | Retained data                                | Use a read-only API login; keep migration/partition-maintenance authority out of public request processes                                                |
| Worker to storage             | Historical evidence and resource budget      | Bounded retention, checksums, idempotent observations; worker needs both storage access and outbound feed access                                         |
| Host to database/cache        | Service credentials and data                 | No public data-service ports in production; loopback ports for local development; protect host and backup directories                                    |
| Build and release             | Repository and deployment integrity          | Locked dependencies, CI tests, protected production branch, environment separation; never give fork previews production secrets                          |

The application does not accept arbitrary URL-fetch requests from public users. Feed and map origins are trusted operator configuration, not an SSRF sandbox. Avoid credential-bearing feed URLs. `/metrics` is intended for local collection and is not routed by the default public proxy.

## Database roles

Production API credentials must be distinct from the database owner and migration credentials. Grant `CONNECT` on the application database, `USAGE` on its schema, and `SELECT` on application tables to a dedicated non-superuser API role. Set matching default table privileges for future migrations. Do not grant schema creation, table ownership, role administration, or membership in a writer role. The worker and aggregation jobs need specific write permissions; partition creation/removal belongs to a trusted maintenance role.

The supplied development Compose credentials are not a least-privilege production configuration. Configure `TP_API_DATABASE_URL` for the production backend, and retain `TP_DATABASE_URL` for trusted migration/worker commands. Validate role privileges in the target installation before exposing its API. Existing installations do not become hardened merely by upgrading application code.

## Verification limits

Dependency audits and source review do not guarantee the absence of vulnerabilities. A deployment requires independent verification of host access, database roles, TLS, restore capability, and resource limits. Long-duration availability and client delivery latency must be measured on the actual host. Synthetic demo results are excluded from those claims.

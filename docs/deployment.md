# Deployment

The TransitPulse web application is deployed on Vercel Hobby through Vercel's
native GitHub integration.

## Git deployment flow

- `main` is the production branch.
- A successful merge to `main` automatically creates a production deployment.
- Pull-request branches automatically create isolated preview deployments.
- The Vercel project root is `apps/web` and the framework preset is Next.js.
- The build runtime follows the repository's Node.js 22 requirement.

Production changes must pass the protected GitHub checks and merge through a
pull request. Do not deploy production from a task branch or by bypassing the
Git integration.

## Environment separation

`NEXT_PUBLIC_APP_ENV` is configured independently:

| Environment | Value         |
| ----------- | ------------- |
| Development | `development` |
| Preview     | `preview`     |
| Production  | `production`  |

Local development defaults are documented in `apps/web/.env.example`.
Credentials and private values must never be committed. Preview and production
must not share credentials when backend integrations are introduced.

Use `NEXT_PUBLIC_DATA_MODE=demo` for the standalone frontend demonstration. Its
same-origin API returns labeled synthetic fixtures and requires no backend secrets.
Use `NEXT_PUBLIC_DATA_MODE=live` and `NEXT_PUBLIC_API_BASE_URL` for a live backend.
These public values are fixed during the frontend build; rebuild after changing
them. Production Docker Compose selects live mode and passes them as build arguments.

## Live container prerequisites

Create a dedicated read-only database role and set `TP_API_DATABASE_URL` before
starting production Compose. The API container receives only that database
credential; migration and worker credentials remain in their own containers.
See [database privilege requirements](security.md#database-roles).

Caddy uses the fixed `TRUSTED_PROXY_IP` on `EDGE_SUBNET`; only that address is
trusted by Uvicorn for forwarded client identity. If the default subnet conflicts
with another local network, change both settings together. Keep the backend port
unpublished and do not configure wildcard proxy trust. Caddy is the public entry
point and replaces untrusted forwarded client headers.

The worker requires outbound access to the configured MBTA feeds. PostgreSQL and
Valkey remain on the internal network. Validate TLS, role grants, backups, and
restart recovery on the selected host before advertising live service.

## Cost boundary

The deployment foundation uses the Vercel Hobby plan. Do not enable paid
features, credit-based resources, or automatic spending without explicit
approval.

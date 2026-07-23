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

| Environment | Value |
| --- | --- |
| Development | `development` |
| Preview | `preview` |
| Production | `production` |

Local development defaults are documented in `apps/web/.env.example`.
Credentials and private values must never be committed. Preview and production
must not share credentials when backend integrations are introduced.

## Cost boundary

The deployment foundation uses the Vercel Hobby plan. Do not enable paid
features, credit-based resources, or automatic spending without explicit
approval.

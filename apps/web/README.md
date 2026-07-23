# TransitPulse web

The frontend is a Next.js App Router application using TypeScript, Tailwind CSS,
and the TransitPulse Signal semantic theme.

## Commands

Run these from the repository root:

```sh
pnpm --filter web dev
pnpm --filter web format
pnpm --filter web lint
pnpm --filter web typecheck
pnpm --filter web test
pnpm --filter web build
pnpm --filter web test:e2e
```

Copy `.env.example` to `.env.local` when local overrides are needed. Only
variables prefixed with `NEXT_PUBLIC_` are exposed to the browser.

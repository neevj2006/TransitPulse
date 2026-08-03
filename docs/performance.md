# Frontend performance budget

TransitPulse keeps rider-facing pages useful on ordinary mobile connections by
deferring optional visualizations and keeping realtime transport scoped to the
pages that need it.

## Accepted budgets

Measured on the production build against a local desktop Chromium audit:

| Measure | Budget | Rationale |
| --- | ---: | --- |
| Lighthouse performance score | 85 or higher | Ensures the public shell remains responsive. |
| First Contentful Paint | 2.0 seconds or less | Riders should see clear context quickly. |
| Largest Contentful Paint | 4.0 seconds or less | The primary page content should render promptly even while data services reconnect. |
| Total Blocking Time | 200 ms or less | Search and navigation should remain usable. |
| Cumulative Layout Shift | 0.10 or less | Arrival and trust information must not jump unexpectedly. |

These are review budgets, not a claim that a localhost audit predicts every
device, network, map-tile, or backend condition. Production and replay checks
remain necessary before publication.

## Implementation choices

- MapLibre and Recharts load only when a page renders its map or chart.
- The service worker caches the app shell and same-origin static build assets
  only. It never caches `/api/` responses, so realtime data cannot be replayed
  as live.
- SSE subscriptions remain component-scoped through the live-query hook; pages
  without live data do not subscribe or rerender for vehicle updates.
- Geist font assets are built and served locally by Next.js with swap behavior.
- Interactive maps always retain a list alternative and loading/failure state.

## Verification

Run from `apps/web` after a production build:

```sh
pnpm build
pnpm start --hostname 127.0.0.1 --port 3200
pnpm dlx lighthouse http://127.0.0.1:3200/ --only-categories=performance
```

Review route chunks after each significant visualization or map change, and
repeat the audit for `/`, `/map`, and `/reliability`.

The initial local production audit of `/` recorded a performance score of 88,
FCP of 1.0 seconds, LCP of 4.0 seconds, TBT of 40 ms, and CLS of 0.006. The
audit ran without a backend, so its pending realtime request is a deliberately
conservative availability condition rather than a claim about a deployed API.

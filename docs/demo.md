# Demonstration

After `pnpm install --frozen-lockfile`, run `pnpm --filter web dev` and open `http://localhost:3000`. With no configured API origin the application defaults to demonstration mode. Set `NEXT_PUBLIC_DATA_MODE=demo` explicitly to use it even when a backend origin is present. The same setting works on a Vercel preview or production build.

The persistent banner and source badges identify demonstration data. The fixture date is July 24, 2026. These are illustrative transit scenarios and synthetic reliability samples, never current travel guidance or a claim about measured MBTA performance.

1. Search **Harvard** and open its arrival board.
2. Change **Scenario** to **Feed outage**. Scheduled departures remain visible without live predictions.
3. Open **Map**, choose **Stale source**, and inspect the text vehicle list. Playback supports pause, 1×, 10×, and restart. Sample vehicles disappear after five minutes of playback.
4. Open **Reliability**. Filter by Red or an unsupported route to exercise populated and empty states. Clear the filter to recover.
5. Open **Transfer**. Enter valid planned times, adjust walking time, and calculate. Probabilities are calculated from illustrative delay pairs, not returned as a canned constant.
6. Open **Operator** to inspect source-health examples. Unmeasured API/cache telemetry remains unavailable instead of displaying fabricated performance numbers.

To use real feeds, select `NEXT_PUBLIC_DATA_MODE=live`, configure `NEXT_PUBLIC_API_BASE_URL`, and follow the [deployment guide](deployment.md). Public environment settings are embedded at build time; rebuild after changing modes. A live installation never switches silently to synthetic results during an outage.

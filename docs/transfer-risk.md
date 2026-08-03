# Transfer-risk baseline

`GET /api/v1/transfer-risk` returns an empirical, reproducible estimate of a
planned connection's missed-transfer probability. It requires arriving and
connecting route and stop IDs, timezone-aware planned arrival and departure
timestamps, and an optional walking-time input in seconds.

The deterministic buffer is `planned departure − planned arrival − walking
time`. The service takes up to the most recent 100 historical arrival-delay
observations for the arriving route/stop and departure-delay observations for
the connecting route/stop, strictly before the requested journey time (and
never after the API request time). It evaluates every arrival/departure pair;
a pair misses when arrival delay plus walking time exceeds the planned gap plus
departure delay. The proportion of missed pairs is the returned probability.

The API returns `UNKNOWN` and no probability unless each leg has at least 20
observations. When no walking value is supplied, a static-GTFS transfer minimum
is used for the matching stop pair, otherwise the documented default is three
minutes for different stops and zero for the same stop. Results include input
source dates, per-leg samples, assumptions, and a calculation version.

Risk labels intentionally use broad bands: Low is at most 15%, Medium is over
15% through 35%, and High is over 35%. This independent-pair baseline does not
model correlation between services, cancellations, platform crowding,
accessibility needs, disruptions, or whether a rider actually made the
connection. It is decision context, not a guarantee.

When credible outcomes accumulate, evaluation labels a historical connection
feasible when its observed arrival plus walking time is no later than its
observed connecting departure. Chronological holdouts must be used to avoid
future leakage. Brier score and calibration plots are deferred until enough
reconciled observations produce credible labels; the MVP exposes that
limitation rather than reporting unstable quality statistics.

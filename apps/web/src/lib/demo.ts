/** Deterministic illustrative fixtures. These are not current MBTA observations. */
export const DEMO_DATE = "2026-07-24";
export const DEMO_START = Date.parse(`${DEMO_DATE}T14:00:00Z`);
export const demoStops = [
  {
    stop_id: "Harvard",
    name: "Harvard",
    latitude: 42.3734,
    longitude: -71.1189,
  },
  {
    stop_id: "Central",
    name: "Central",
    latitude: 42.3655,
    longitude: -71.1038,
  },
  {
    stop_id: "DowntownCrossing",
    name: "Downtown Crossing",
    latitude: 42.3555,
    longitude: -71.0605,
  },
];
const routes = ["Red", "Orange", "Green-B"];
const arrivalDelays = [
  0, 30, 60, 90, 120, 150, 180, 210, 240, 300, 360, 420, 480, 540, 600, 660,
  720, 780, 840, 900,
];
const departureDelays = [
  0, 0, 0, 0, 0, 30, 30, 30, 60, 60, 60, 60, 90, 90, 120, 120, 150, 180, 240,
  300,
];

export function demoResponse(url: URL): { status: number; body: unknown } {
  const path = decodeURIComponent(url.pathname);
  const params = url.searchParams;
  const seconds = Math.min(
    3600,
    Math.max(0, Number(params.get("demo_seconds")) || 0),
  );
  const now = new Date(DEMO_START + seconds * 1000).toISOString();
  const scenario = params.get("demo_scenario") ?? "healthy";
  const stale = scenario === "stale";
  const unavailable = scenario === "outage";
  const freshness = {
    state: stale ? "STALE" : "HEALTHY",
    age_seconds: stale ? 180 : 0,
  };
  const meta = {
    mode: "demonstration",
    synthetic: true,
    generated_at: now,
    source_date: DEMO_DATE,
  };
  const ok = (data: unknown, extra = {}) => ({
    status: 200,
    body: { schema_version: "1.0.0", data, meta: { ...meta, ...extra } },
  });
  const fail = (status: number, message: string) => ({
    status,
    body: { code: "DEMO_REQUEST", message },
  });
  if (path.endsWith("/search")) {
    const q = (params.get("q") ?? "").toLowerCase();
    return ok(
      [
        ...routes.map((id) => ({
          kind: "route",
          id,
          label: id,
          detail: `${id} Line`,
        })),
        ...demoStops.map((stop) => ({
          kind: "stop",
          id: stop.stop_id,
          label: stop.name,
          detail: "Demonstration stop",
        })),
      ].filter((item) =>
        `${item.label} ${item.detail}`.toLowerCase().includes(q),
      ),
    );
  }
  if (path.endsWith("/live/health"))
    return ok(
      ["vehicles", "trip-updates", "alerts"].map((source_id) => ({
        source_id,
        state: unavailable ? "OFFLINE" : freshness.state,
        last_success_at: new Date(DEMO_START).toISOString(),
        entity_counts: { accepted: unavailable ? 0 : 3 },
        rejection_counts: { parser_errors: 0, unreconciled: 0 },
      })),
      {
        api_latency: { p50_ms: null, p95_ms: null },
        cache_telemetry: null,
        quality_events: [],
        recent_polls: unavailable
          ? [{ source_id: "vehicles", outcome: "TIMEOUT", completed_at: now }]
          : [],
      },
    );
  if (path.endsWith("/vehicles"))
    return ok(
      unavailable || seconds > 300
        ? []
        : routes
            .filter(
              (id) =>
                !path.includes("/routes/") || path.includes(`/routes/${id}/`),
            )
            .map((route_id, i) => ({
              vehicle_id: `demo-${i}`,
              route_id,
              trip_id: `demo-trip-${i}`,
              latitude: 42.36 + i * 0.005 + Math.min(seconds, 180) * 0.00001,
              longitude: -71.08 + i * 0.01,
              freshness,
            })),
    );
  if (path.endsWith("/alerts"))
    return ok(
      unavailable
        ? []
        : [
            {
              alert_id: "demo-alert",
              header: "Demonstration: shuttle buses",
              description:
                "Illustrative disruption scenario. This is not an active agency notice.",
              effect: "SHUTTLE",
              route_ids: ["Red"],
              stop_ids: ["Harvard"],
              source_timestamp: now,
              freshness,
            },
          ].filter(
            (item) =>
              !params.get("route_id") ||
              item.route_ids.includes(params.get("route_id")!),
          ),
    );
  if (path.includes("/arrivals")) {
    const stop = path.split("/stops/")[1]?.split("/")[0];
    if (!demoStops.some((item) => item.stop_id === stop))
      return fail(404, "Stop is outside the demonstration network.");
    if (path.includes("/live/"))
      return ok(
        unavailable
          ? []
          : [
              {
                trip_id: "demo-trip-0",
                route_id: "Red",
                agency_prediction: {
                  arrival_time: new Date(DEMO_START + 360000).toISOString(),
                  departure_time: null,
                },
                freshness,
                scheduled_fallback: null,
              },
            ],
      );
    return ok(
      [0, 1, 2].map((i) => ({
        trip_id: `demo-trip-${i}`,
        route_id: "Red",
        headsign: "Alewife",
        scheduled: {
          service_date: DEMO_DATE,
          gtfs_seconds: 36000 + 300 + i * 600,
        },
      })),
    );
  }
  if (path.includes("/routes/") && path.endsWith("/stops")) {
    if (!routes.some((id) => path.includes(`/routes/${id}/`)))
      return fail(404, "Route is outside the demonstration network.");
    const reversed = params.get("direction_id") === "1";
    return ok({
      directions: [0, 1],
      headsign: reversed ? "Downtown Crossing" : "Harvard",
      stops: (reversed ? [...demoStops].reverse() : demoStops).map(
        (stop, i) => ({
          ...stop,
          sequence: i + 1,
          scheduled_seconds: 36000 + i * 300,
        }),
      ),
    });
  }
  if (path.endsWith("/stops/nearby")) {
    const lat = Number(params.get("latitude")),
      lon = Number(params.get("longitude"));
    if (
      !Number.isFinite(lat) ||
      !Number.isFinite(lon) ||
      Math.abs(lat) > 90 ||
      Math.abs(lon) > 180
    )
      return fail(422, "Invalid coordinates.");
    return ok(
      demoStops
        .map((stop) => ({
          ...stop,
          distance_metres: Math.round(
            Math.hypot(
              (lat - stop.latitude) * 111000,
              (lon - stop.longitude) * 82000,
            ),
          ),
        }))
        .sort((a, b) => a.distance_metres - b.distance_metres),
    );
  }
  if (path.endsWith("/reliability"))
    return ok(
      routes
        .flatMap((route_id) =>
          [8, 9, 10].map((hour) => ({
            route_id,
            direction_id: 0,
            stop_id: "Harvard",
            weekday: 5,
            service_date: DEMO_DATE,
            hour,
            sample_size: 20,
            coverage: 1,
            median_delay_seconds: 330,
            p95_delay_seconds: 843,
            on_time_percentage: 0.5,
          })),
        )
        .filter((row) =>
          ["route_id", "direction_id", "stop_id", "weekday", "hour"].every(
            (key) =>
              !params.has(key) ||
              String(row[key as keyof typeof row]) === params.get(key),
          ),
        ),
      {
        metric_definition: "illustrative-demo-v1",
        minimum_sample_size: 20,
        minimum_coverage: 0.8,
      },
    );
  if (path.endsWith("/transfer-risk")) {
    const arrival = Date.parse(params.get("planned_arrival") ?? ""),
      departure = Date.parse(params.get("planned_departure") ?? "");
    const walking = Number(params.get("walking_seconds") ?? "180");
    if (
      !Number.isFinite(arrival) ||
      !Number.isFinite(departure) ||
      departure <= arrival ||
      !Number.isFinite(walking) ||
      walking < 0 ||
      walking > 3600
    )
      return fail(
        422,
        "Use valid times with departure after arrival and 0–60 minutes walking.",
      );
    const supported =
      ["arriving_route_id", "connecting_route_id"].every((key) =>
        routes.includes(params.get(key) ?? ""),
      ) &&
      ["arriving_stop_id", "connecting_stop_id"].every((key) =>
        demoStops.some((stop) => stop.stop_id === params.get(key)),
      );
    const buffer = (departure - arrival) / 1000 - walking;
    const misses = arrivalDelays
      .flatMap((a) => departureDelays.map((d) => a - d > buffer))
      .filter(Boolean).length;
    const probability =
      misses / (arrivalDelays.length * departureDelays.length);
    return ok(
      {
        sufficient_data: supported,
        missed_transfer_probability: supported ? probability : null,
        risk_band: !supported
          ? "UNKNOWN"
          : probability < 0.2
            ? "LOW"
            : probability < 0.5
              ? "MEDIUM"
              : "HIGH",
        planned_buffer_seconds: buffer,
        walking_seconds: walking,
        walking_time_source: "user",
        sample_size: supported ? 20 : 0,
        arrival_sample_size: supported ? 20 : 0,
        departure_sample_size: supported ? 20 : 0,
        source_first_at: new Date(DEMO_START).toISOString(),
        source_last_at: now,
        history_stale: true,
        assumptions: [
          "Demonstration only: illustrative delay samples, not measured MBTA reliability.",
          "Arrival and departure delays are treated as independent.",
          "Walking time is a user assumption; no connection is guaranteed.",
        ],
      },
      { calculation_version: "illustrative-demo-v1" },
    );
  }
  return fail(404, "This endpoint is not part of the demonstration.");
}

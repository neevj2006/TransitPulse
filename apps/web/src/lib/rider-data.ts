import { z } from "zod";
import { apiRequest } from "@/lib/api";

const envelope = <T extends z.ZodType>(data: T) =>
  z.object({ data, meta: z.record(z.string(), z.unknown()).optional() });

const freshness = z.object({
  state: z.enum(["HEALTHY", "STALE", "UNKNOWN"]).optional(),
  age_seconds: z.number().nullable().optional(),
});

export const vehicleSchema = z.object({
  vehicle_id: z.string(),
  route_id: z.string().nullable(),
  trip_id: z.string().nullable(),
  latitude: z.number(),
  longitude: z.number(),
  freshness,
});
export type RiderVehicle = z.infer<typeof vehicleSchema>;

export const alertSchema = z.object({
  alert_id: z.string(),
  header: z.string().nullable().optional(),
  description: z.string().nullable().optional(),
  effect: z.string().nullable().optional(),
  route_ids: z.array(z.string()).default([]),
  stop_ids: z.array(z.string()).default([]),
  source_timestamp: z.string().nullable().optional(),
  active_periods: z.array(z.unknown()).optional(),
  freshness,
});
export type RiderAlert = z.infer<typeof alertSchema>;

export const scheduledArrivalSchema = z.object({
  trip_id: z.string(),
  route_id: z.string(),
  headsign: z.string().nullable().optional(),
  scheduled: z.object({
    service_date: z.string(),
    gtfs_seconds: z.number().nullable(),
  }),
});
export const liveArrivalSchema = z.object({
  trip_id: z.string(),
  route_id: z.string().nullable(),
  agency_prediction: z
    .object({
      arrival_time: z.string().nullable(),
      departure_time: z.string().nullable(),
    })
    .nullable(),
  freshness,
  scheduled_fallback: z
    .object({ gtfs_seconds: z.number().nullable() })
    .nullable(),
});

export function scheduledArrivals(stopId: string, serviceDate: string) {
  return apiRequest(
    `/api/v1/stops/${encodeURIComponent(stopId)}/arrivals?service_date=${serviceDate}`,
    envelope(z.array(scheduledArrivalSchema)),
  ).then((value) => value.data);
}
export function liveArrivals(stopId: string) {
  return apiRequest(
    `/api/v1/live/stops/${encodeURIComponent(stopId)}/arrivals`,
    envelope(z.array(liveArrivalSchema)),
  ).then((value) => value.data);
}
export function routeVehicles(routeId: string) {
  return apiRequest(
    `/api/v1/live/routes/${encodeURIComponent(routeId)}/vehicles`,
    envelope(z.array(vehicleSchema)),
  ).then((value) => value.data);
}
export const routeStopsSchema = z.object({
  directions: z.array(z.number()),
  headsign: z.string().nullable().optional(),
  stops: z.array(
    z.object({
      stop_id: z.string(),
      name: z.string(),
      sequence: z.number(),
      scheduled_seconds: z.number().nullable(),
    }),
  ),
});
export function routeStops(routeId: string, direction?: number) {
  const suffix = direction === undefined ? "" : `?direction_id=${direction}`;
  return apiRequest(
    `/api/v1/routes/${encodeURIComponent(routeId)}/stops${suffix}`,
    envelope(routeStopsSchema),
  ).then((value) => value.data);
}
export function systemVehicles() {
  return apiRequest(
    "/api/v1/live/vehicles",
    envelope(z.array(vehicleSchema)),
  ).then((value) => value.data);
}
export function alerts(filters: { routeId?: string; stopId?: string } = {}) {
  const query = new URLSearchParams();
  if (filters.routeId) query.set("route_id", filters.routeId);
  if (filters.stopId) query.set("stop_id", filters.stopId);
  return apiRequest(
    `/api/v1/live/alerts${query.size ? `?${query}` : ""}`,
    envelope(z.array(alertSchema)),
  ).then((value) => value.data);
}
export function liveHealth() {
  return apiRequest(
    "/api/v1/live/health",
    z.object({
      data: z.array(z.object({ state: z.string().optional() })).default([]),
    }),
  );
}

export function serviceDate() {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/New_York",
  }).format(new Date());
}
export function formatGtfsTime(seconds: number | null | undefined) {
  if (seconds === null || seconds === undefined)
    return "Scheduled time unavailable";
  const day = Math.floor(seconds / 86_400);
  const date = new Date(Date.UTC(2000, 0, 1 + day, 0, 0, seconds % 86_400));
  return `${new Intl.DateTimeFormat("en-US", { hour: "numeric", minute: "2-digit", timeZone: "UTC" }).format(date)}${day ? " (+1 day)" : ""}`;
}
export function formatTimestamp(value: string | null | undefined) {
  if (!value) return "Unknown";
  return new Intl.DateTimeFormat("en-US", {
    hour: "numeric",
    minute: "2-digit",
    timeZone: "America/New_York",
  }).format(new Date(value));
}

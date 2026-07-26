import { z } from "zod";
import { apiRequest } from "@/lib/api";

export const searchResultSchema = z.object({
  kind: z.enum(["route", "stop", "destination"]),
  id: z.string(),
  label: z.string(),
  detail: z.string().nullable(),
  route_color: z.string().optional(),
});
const envelope = z.object({ data: z.array(searchResultSchema) });
export type SearchResult = z.infer<typeof searchResultSchema>;

export function searchNetwork(query: string) {
  return apiRequest(
    `/api/v1/search?q=${encodeURIComponent(query)}`,
    envelope,
  ).then((item) => item.data);
}

export function nearbyStops(latitude: number, longitude: number) {
  return apiRequest(
    `/api/v1/stops/nearby?latitude=${latitude}&longitude=${longitude}`,
    z.object({
      data: z.array(
        z.object({
          stop_id: z.string(),
          name: z.string(),
          distance_metres: z.number(),
        }),
      ),
    }),
  ).then((item) => item.data);
}

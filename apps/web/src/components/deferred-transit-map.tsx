"use client";

import dynamic from "next/dynamic";
import type { Feature, LineString, Point } from "geojson";
import { LoadingSkeleton } from "@/components/trust";

const TransitMap = dynamic(
  () => import("@/components/transit-map").then((module) => module.TransitMap),
  {
    ssr: false,
    loading: () => <LoadingSkeleton label="Loading interactive map" />,
  },
);

export function DeferredTransitMap({
  routeName,
  routeLine,
  stops,
  vehicles,
}: {
  routeName: string;
  routeLine?: Feature<LineString>;
  stops?: Feature<Point>[];
  vehicles?: Feature<Point>[];
}) {
  return (
    <TransitMap
      routeName={routeName}
      routeLine={routeLine}
      stops={stops}
      vehicles={vehicles}
    />
  );
}

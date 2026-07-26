"use client";

import { useEffect, useRef, useState } from "react";
import type { Feature, LineString, Point } from "geojson";
import { Map } from "maplibre-gl";
import { LocateFixed, RotateCcw } from "lucide-react";
import { useTheme } from "next-themes";
import { publicEnv } from "@/lib/env";
import "maplibre-gl/dist/maplibre-gl.css";

type TransitMapProps = {
  routeName: string;
  routeLine?: Feature<LineString>;
  stops?: Feature<Point>[];
  vehicles?: Feature<Point>[];
};

export function TransitMap({
  routeName,
  routeLine,
  stops = [],
  vehicles = [],
}: TransitMapProps) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<Map | null>(null);
  const [failed, setFailed] = useState(false);
  const { resolvedTheme } = useTheme();

  useEffect(() => {
    if (!container.current) return;
    const map = new Map({
      container: container.current,
      center: [-71.06, 42.36],
      zoom: 10,
      style:
        resolvedTheme === "dark"
          ? publicEnv.NEXT_PUBLIC_MAP_STYLE_DARK_URL
          : publicEnv.NEXT_PUBLIC_MAP_STYLE_LIGHT_URL,
      attributionControl: false,
    });
    mapRef.current = map;
    map.on("load", () => {
      const token = (name: string) =>
        getComputedStyle(document.documentElement)
          .getPropertyValue(name)
          .trim();
      map.addSource("route", {
        type: "geojson",
        data: routeLine ?? { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: "route-casing",
        type: "line",
        source: "route",
        paint: {
          "line-color": token("--text"),
          "line-width": 10,
          "line-opacity": 0.6,
        },
      });
      map.addLayer({
        id: "route-line",
        type: "line",
        source: "route",
        paint: {
          "line-color": ["coalesce", ["get", "color"], token("--brand")],
          "line-width": 6,
        },
      });
      map.addSource("stops", {
        type: "geojson",
        data: { type: "FeatureCollection", features: stops },
      });
      map.addLayer({
        id: "stop-markers",
        type: "circle",
        source: "stops",
        paint: {
          "circle-radius": 5,
          "circle-color": token("--surface"),
          "circle-stroke-color": token("--text"),
          "circle-stroke-width": 2,
        },
      });
      map.addSource("vehicles", {
        type: "geojson",
        data: { type: "FeatureCollection", features: vehicles },
      });
      map.addLayer({
        id: "vehicle-markers",
        type: "circle",
        source: "vehicles",
        paint: {
          "circle-radius": 10,
          "circle-color": ["coalesce", ["get", "color"], token("--brand")],
          "circle-stroke-color": token("--surface"),
          "circle-stroke-width": 2,
        },
      });
    });
    map.on("error", () => setFailed(true));
    return () => {
      mapRef.current = null;
      map.remove();
    };
  }, [resolvedTheme, routeLine, stops, vehicles]);

  return (
    <section
      aria-labelledby="map-heading"
      className="bg-surface overflow-hidden rounded-xl border"
    >
      <div className="flex items-center justify-between border-b p-4">
        <h2 id="map-heading" className="font-semibold">
          {routeName} map
        </h2>
        <a className="text-brand text-sm underline" href="#stop-list">
          Skip to stop list
        </a>
      </div>
      {failed ? (
        <p className="text-muted p-4">
          Map tiles are unavailable. Use the stop list below.
        </p>
      ) : (
        <div className="relative">
          <div
            ref={container}
            className="h-80"
            aria-label={`${routeName} map`}
          />
          <div className="absolute top-3 right-3 flex gap-2">
            <button
              type="button"
              aria-label="Recenter map"
              onClick={() =>
                mapRef.current?.jumpTo({ center: [-71.06, 42.36], zoom: 10 })
              }
              className="bg-surface grid size-11 place-items-center rounded-md border shadow-sm"
            >
              <LocateFixed aria-hidden="true" className="size-5" />
            </button>
            <button
              type="button"
              aria-label="Reset map bearing"
              onClick={() => mapRef.current?.resetNorth()}
              className="bg-surface grid size-11 place-items-center rounded-md border shadow-sm"
            >
              <RotateCcw aria-hidden="true" className="size-5" />
            </button>
          </div>
        </div>
      )}
      <p className="text-muted border-t p-3 text-xs">
        Map data © OpenStreetMap contributors · Tiles by OpenFreeMap
      </p>
    </section>
  );
}

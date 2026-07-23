"use client";

import { useEffect, useRef, useState } from "react";
import { Map } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

type TransitMapProps = { routeName: string };

export function TransitMap({ routeName }: TransitMapProps) {
  const container = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!container.current) return;
    const map = new Map({
      container: container.current,
      center: [-71.06, 42.36],
      zoom: 10,
      style: "https://tiles.openfreemap.org/styles/liberty",
    });
    map.on("error", () => setFailed(true));
    return () => map.remove();
  }, []);

  return (
    <section aria-labelledby="map-heading" className="overflow-hidden rounded-xl border bg-surface">
      <div className="flex items-center justify-between border-b p-4">
        <h2 id="map-heading" className="font-semibold">{routeName} map</h2>
        <a className="text-sm text-brand underline" href="#stop-list">Skip to stop list</a>
      </div>
      {failed ? <p className="p-4 text-muted">Map tiles are unavailable. Use the stop list below.</p> : <div ref={container} className="h-80" aria-label={`${routeName} map`} />}
      <p className="border-t p-3 text-xs text-muted">Map data © OpenStreetMap contributors · Tiles by OpenFreeMap</p>
    </section>
  );
}

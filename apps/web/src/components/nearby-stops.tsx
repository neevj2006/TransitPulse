"use client";
import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { nearbyStops } from "@/lib/search";
import { StatePanel } from "@/components/trust";

export function NearbyStops() {
  const [position, setPosition] = useState<GeolocationCoordinates | null>(null);
  const [message, setMessage] = useState<string>();
  const result = useQuery({
    queryKey: ["nearby", position?.latitude, position?.longitude],
    queryFn: () => nearbyStops(position!.latitude, position!.longitude),
    enabled: Boolean(position),
  });
  const request = () => {
    if (!navigator.geolocation) {
      setMessage(
        "Your browser does not support location. Search for a stop instead.",
      );
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (value) => setPosition(value.coords),
      (error) =>
        setMessage(
          error.code === error.PERMISSION_DENIED
            ? "Location permission was not granted. Search for a stop instead."
            : "We could not determine your location. Try again or search for a stop.",
        ),
      { enableHighAccuracy: false, timeout: 10_000 },
    );
  };
  return (
    <section className="card">
      <h2 className="text-xl font-semibold">Nearby stops</h2>
      <p className="text-muted mt-1 text-sm">
        Location is requested only when you choose this action.
      </p>
      {!position ? (
        <button
          type="button"
          onClick={request}
          className="bg-brand-strong mt-4 min-h-11 rounded-md px-4 font-semibold text-white"
        >
          Find nearby stops
        </button>
      ) : null}
      {message ? <p className="text-muted mt-3 text-sm">{message}</p> : null}
      {result.isError ? (
        <StatePanel kind="unknown" title="Nearby stops unavailable">
          Search manually while the service reconnects.
        </StatePanel>
      ) : null}
      {result.data ? (
        <ul className="mt-4 divide-y">
          {result.data.map((stop) => (
            <li key={stop.stop_id}>
              <Link
                className="flex min-h-11 items-center justify-between py-2 underline"
                href={`/stops/${encodeURIComponent(stop.stop_id)}`}
              >
                {stop.name}
                <span className="text-muted no-underline">
                  {stop.distance_metres} m
                </span>
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

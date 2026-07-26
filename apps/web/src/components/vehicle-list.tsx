"use client";
import { useState } from "react";
import { StatePanel, SourceBadge } from "@/components/trust";

export type Vehicle = {
  id: string;
  route: string;
  nextStop?: string;
  state: "live" | "stale" | "unknown";
};
export function VehicleList({ vehicles }: { vehicles: Vehicle[] }) {
  const [selected, setSelected] = useState<Vehicle>();
  if (!vehicles.length)
    return (
      <StatePanel kind="empty" title="No live vehicles to show">
        Vehicle positions appear only while fresh source data is available.
      </StatePanel>
    );
  return (
    <section className="card">
      <h2 className="text-xl font-semibold">Vehicle list</h2>
      <ul className="mt-3 divide-y">
        {vehicles.map((vehicle) => (
          <li key={vehicle.id}>
            <button
              className="flex min-h-12 w-full items-center justify-between text-left"
              onClick={() => setSelected(vehicle)}
            >
              <span>
                {vehicle.route} · {vehicle.nextStop ?? "Next stop unknown"}
              </span>
              <SourceBadge kind={vehicle.state} />
            </button>
          </li>
        ))}
      </ul>
      {selected ? (
        <section
          className="bg-surface-raised mt-4 rounded-lg border p-4"
          aria-label="Vehicle detail"
        >
          <h3 className="font-semibold">{selected.route} vehicle</h3>
          <p className="text-muted mt-1">
            Next stop: {selected.nextStop ?? "Unknown"}
          </p>
          <button
            className="text-brand mt-3 underline"
            onClick={() => setSelected(undefined)}
          >
            Close vehicle detail
          </button>
        </section>
      ) : null}
    </section>
  );
}

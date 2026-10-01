"use client";
import { useSyncExternalStore } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  configureDemo,
  demoSnapshot,
  demoServerSnapshot,
  subscribeDemo,
} from "@/lib/demo-clock";
import { isDemo } from "@/lib/env";

export function DemoBanner() {
  const { speed, scenario } = useSyncExternalStore(
    subscribeDemo,
    demoSnapshot,
    demoServerSnapshot,
  );
  const client = useQueryClient();
  if (!isDemo) return null;
  const update = (nextSpeed: number, nextScenario: string, reset = false) => {
    configureDemo(nextSpeed, nextScenario, reset);
    void client.invalidateQueries();
  };
  return (
    <aside
      className="bg-status-warning-surface text-status-warning border-b px-4 py-3"
      aria-label="Demonstration controls"
    >
      <div className="mx-auto max-w-7xl space-y-2">
        <p>
          <strong>Demonstration data — not live travel guidance.</strong>{" "}
          Illustrative July 24, 2026 scenarios; metrics are synthetic.
        </p>
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <label>
            Playback{" "}
            <select
              className="bg-surface min-h-11 rounded-md border px-3"
              value={speed}
              onChange={(e) => update(Number(e.target.value), scenario)}
            >
              <option value={0}>Paused</option>
              <option value={1}>1×</option>
              <option value={10}>10×</option>
            </select>
          </label>
          <label>
            Scenario{" "}
            <select
              className="bg-surface min-h-11 rounded-md border px-3"
              value={scenario}
              onChange={(e) => update(speed, e.target.value)}
            >
              <option value="healthy">Healthy sample</option>
              <option value="stale">Stale source</option>
              <option value="outage">Feed outage</option>
            </select>
          </label>
          <button
            className="min-h-11 rounded-md border px-3"
            onClick={() => update(speed, scenario, true)}
          >
            Restart replay
          </button>
        </div>
      </div>
    </aside>
  );
}

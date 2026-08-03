"use client";

import dynamic from "next/dynamic";
import type { ChartDatum } from "@/components/accessible-chart-client";

export type { ChartDatum } from "@/components/accessible-chart-client";

const AccessibleLineChartClient = dynamic(
  () =>
    import("@/components/accessible-chart-client").then(
      (module) => module.AccessibleLineChartClient,
    ),
  {
    ssr: false,
    loading: () => (
      <section className="card" aria-busy="true" aria-label="Loading chart">
        <div className="bg-surface-muted h-6 w-48 rounded" />
        <div className="bg-surface-muted mt-4 h-72 rounded" />
      </section>
    ),
  },
);

export function AccessibleLineChart({
  title,
  takeaway,
  data,
  coverage,
}: {
  title: string;
  takeaway: string;
  data: ChartDatum[];
  coverage?: string;
}) {
  return (
    <AccessibleLineChartClient
      title={title}
      takeaway={takeaway}
      data={data}
      coverage={coverage}
    />
  );
}

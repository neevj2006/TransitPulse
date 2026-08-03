"use client";

import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { CoverageLabel } from "@/components/trust";

export type ChartDatum = { label: string; value: number };

export function AccessibleLineChartClient({
  title,
  takeaway,
  data,
  coverage = "No data",
}: {
  title: string;
  takeaway: string;
  data: ChartDatum[];
  coverage?: string;
}) {
  return (
    <section className="card" aria-labelledby="chart-title">
      <h2 id="chart-title" className="text-xl font-semibold">
        {title}
      </h2>
      <p className="text-muted mt-1 text-sm">{takeaway}</p>
      {data.length ? (
        <>
          <div className="mt-4 h-72" aria-label={`${title} chart`}>
            <ResponsiveContainer>
              <LineChart data={data}>
                <XAxis dataKey="label" />
                <YAxis />
                <Tooltip />
                <Line
                  dataKey="value"
                  stroke="var(--brand)"
                  strokeWidth={3}
                  dot
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <details className="mt-4">
            <summary className="text-brand cursor-pointer font-medium underline">
              View data table
            </summary>
            <table className="mt-3 w-full text-left text-sm">
              <caption className="sr-only">{title} data</caption>
              <thead>
                <tr>
                  <th scope="col">Period</th>
                  <th scope="col">Value</th>
                </tr>
              </thead>
              <tbody>
                {data.map((row) => (
                  <tr className="border-t" key={row.label}>
                    <th className="py-2" scope="row">
                      {row.label}
                    </th>
                    <td className="py-2 font-mono">{row.value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
        </>
      ) : (
        <p className="text-muted bg-surface-muted mt-4 rounded-md p-4">
          No chart data is available for these filters.
        </p>
      )}
      <div className="mt-4">
        <CoverageLabel coverage={coverage} />
      </div>
    </section>
  );
}

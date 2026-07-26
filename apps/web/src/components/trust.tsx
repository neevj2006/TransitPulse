import {
  CalendarClock,
  CircleAlert,
  CircleHelp,
  CloudOff,
  Database,
  Radio,
  Sparkles,
  TriangleAlert,
} from "lucide-react";

export type SourceKind =
  | "live"
  | "scheduled"
  | "observed"
  | "estimate"
  | "stale"
  | "unknown"
  | "offline";

const sourceConfig = {
  live: {
    label: "Live",
    icon: Radio,
    className: "bg-status-live-surface text-status-live",
  },
  scheduled: {
    label: "Scheduled",
    icon: CalendarClock,
    className: "bg-status-scheduled-surface text-status-scheduled",
  },
  observed: {
    label: "Observed",
    icon: Database,
    className: "bg-status-observed-surface text-status-observed",
  },
  estimate: {
    label: "TransitPulse estimate",
    icon: Sparkles,
    className: "bg-status-estimate-surface text-status-estimate",
  },
  stale: {
    label: "Stale",
    icon: TriangleAlert,
    className: "bg-status-warning-surface text-status-warning",
  },
  unknown: {
    label: "Unknown",
    icon: CircleHelp,
    className: "bg-status-scheduled-surface text-status-scheduled",
  },
  offline: {
    label: "Offline",
    icon: CloudOff,
    className: "bg-status-offline-surface text-status-offline",
  },
} as const;

export function SourceBadge({ kind, age }: { kind: SourceKind; age?: string }) {
  const config = sourceConfig[kind];
  const Icon = config.icon;
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm font-semibold ${config.className}`}
    >
      <Icon aria-hidden="true" className="size-4" />
      {config.label}
      {age ? ` · ${age}` : ""}
    </span>
  );
}

export function DataValue({
  value,
  kind,
  detail,
}: {
  value: string;
  kind: SourceKind;
  detail?: string;
}) {
  return (
    <div className="space-y-1">
      <p className="font-mono text-xl font-semibold tabular-nums">{value}</p>
      <SourceBadge kind={kind} />
      {detail ? <p className="text-muted text-sm">{detail}</p> : null}
    </div>
  );
}

export function EstimatedRange({
  range,
  confidence,
}: {
  range: string;
  confidence?: string;
}) {
  return <DataValue value={range} kind="estimate" detail={confidence} />;
}
export function CoverageLabel({
  coverage,
  samples,
}: {
  coverage: string;
  samples?: number;
}) {
  return (
    <p className="text-muted text-sm">
      Coverage {coverage}
      {samples !== undefined ? ` · ${samples.toLocaleString()} samples` : ""}
    </p>
  );
}

export function StatePanel({
  kind,
  title,
  children,
}: {
  kind: "stale" | "fallback" | "unknown" | "offline" | "empty";
  title: string;
  children: React.ReactNode;
}) {
  const source: SourceKind =
    kind === "fallback" ? "scheduled" : kind === "empty" ? "unknown" : kind;
  const Icon =
    kind === "fallback"
      ? CalendarClock
      : kind === "stale"
        ? TriangleAlert
        : kind === "offline"
          ? CloudOff
          : CircleAlert;
  return (
    <section className="card flex gap-3" aria-label={title}>
      <span
        className={`grid size-10 shrink-0 place-items-center rounded-full ${sourceConfig[source].className}`}
      >
        <Icon aria-hidden="true" className="size-5" />
      </span>
      <div>
        <h2 className="font-semibold">{title}</h2>
        <div className="text-muted mt-1 text-sm leading-6">{children}</div>
      </div>
    </section>
  );
}

export function LoadingSkeleton({
  label = "Loading content",
}: {
  label?: string;
}) {
  return (
    <div aria-label={label} aria-busy="true" className="card space-y-3">
      <div className="bg-surface-muted h-5 w-1/3 rounded" />
      <div className="bg-surface-muted h-4 w-full rounded" />
      <div className="bg-surface-muted h-4 w-2/3 rounded" />
    </div>
  );
}

export function ServiceAlert({
  title,
  children,
  severity = "warning",
}: {
  title: string;
  children: React.ReactNode;
  severity?: "warning" | "error";
}) {
  const tone =
    severity === "error"
      ? "bg-status-error-surface text-status-error"
      : "bg-status-warning-surface text-status-warning";
  return (
    <section
      className={`rounded-lg border p-4 ${tone}`}
      role={severity === "error" ? "alert" : undefined}
    >
      <div className="flex gap-2">
        <CircleAlert aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
        <div>
          <h2 className="font-semibold">{title}</h2>
          <p className="mt-1 text-sm leading-6">{children}</p>
        </div>
      </div>
    </section>
  );
}

import type { LucideIcon } from "lucide-react";

type StatusCardProps = {
  description: string;
  icon: LucideIcon;
  label: string;
  tone: "success" | "unknown";
  value: string;
};

export function StatusCard({
  description,
  icon: Icon,
  label,
  tone,
  value,
}: StatusCardProps) {
  const toneClass =
    tone === "success"
      ? "bg-status-success-surface text-status-success"
      : "bg-status-unknown-surface text-status-unknown";

  return (
    <article className="bg-surface rounded-xl border p-5 shadow-sm">
      <div
        className={`mb-4 inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm font-semibold ${toneClass}`}
      >
        <Icon aria-hidden="true" className="size-4" />
        {label}
      </div>
      <p className="text-text font-mono text-lg font-semibold">{value}</p>
      <p className="text-muted mt-2 text-sm leading-6">{description}</p>
    </article>
  );
}

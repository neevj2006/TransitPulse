import { AppShell } from "@/components/app-shell";
export default function AccessibilityPage() {
  return (
    <AppShell>
      <article className="max-w-3xl space-y-4">
        <h1 className="text-3xl font-semibold">Accessibility</h1>
        <p>
          TransitPulse supports keyboard navigation, visible focus, light and
          dark themes, and list or table alternatives for maps and charts.
        </p>
        <p className="text-muted">
          Transit source data may have limitations. Unknown accessibility facts
          are shown as unknown rather than inferred.
        </p>
      </article>
    </AppShell>
  );
}

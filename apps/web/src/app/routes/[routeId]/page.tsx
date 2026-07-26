import { AppShell } from "@/components/app-shell";
import { RouteDetail } from "@/components/route-detail";
import { RouteBadge } from "@/components/route-badge";

export default async function RoutePage({
  params,
}: {
  params: Promise<{ routeId: string }>;
}) {
  const { routeId } = await params;
  return (
    <AppShell>
      <header className="flex items-center gap-3">
        <RouteBadge label={routeId} />
        <div>
          <p className="text-brand text-sm font-semibold">Route</p>
          <h1 className="text-3xl font-semibold">{routeId}</h1>
        </div>
      </header>
      <RouteDetail routeId={routeId} />
    </AppShell>
  );
}

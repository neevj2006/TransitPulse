import { AppShell } from "@/components/app-shell";
import { AlertList } from "@/components/alert-list";
export default function AlertsPage() {
  return (
    <AppShell>
      <header>
        <p className="text-brand text-sm font-semibold">Agency notices</p>
        <h1 className="mt-1 text-3xl font-semibold">Service alerts</h1>
      </header>
      <AlertList />
    </AppShell>
  );
}

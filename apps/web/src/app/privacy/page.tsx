import { AppShell } from "@/components/app-shell";
export default function PrivacyPage() {
  return (
    <AppShell>
      <article className="max-w-3xl space-y-4">
        <h1 className="text-3xl font-semibold">Privacy</h1>
        <p>
          TransitPulse requests location only after you choose a nearby-stops
          feature. Location is not required to search the network.
        </p>
        <p className="text-muted">
          This MVP does not require an account. Any future local preferences
          will be described before they are stored.
        </p>
      </article>
    </AppShell>
  );
}

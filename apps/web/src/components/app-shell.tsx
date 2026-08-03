import Link from "next/link";
import {
  Activity,
  BarChart3,
  Map,
  Menu,
  Search,
  ShieldAlert,
  Timer,
} from "lucide-react";
import { ThemeSelect } from "@/components/theme-select";
import { NetworkStatusStrip } from "@/components/network-status-strip";

const riderLinks = [
  { href: "/", label: "Home", icon: Search },
  { href: "/map", label: "Map", icon: Map },
  { href: "/alerts", label: "Alerts", icon: ShieldAlert },
  { href: "/reliability", label: "Reliability", icon: BarChart3 },
  { href: "/transfer-risk", label: "Transfer", icon: Timer },
];
const operatorLinks = [
  { href: "/operator", label: "Overview", icon: Activity },
  { href: "/operator/feeds", label: "Feed health", icon: Activity },
  { href: "/operator/routes", label: "Routes", icon: BarChart3 },
  { href: "/operator/system", label: "System", icon: Activity },
];

export function AppShell({
  children,
  operator = false,
}: {
  children: React.ReactNode;
  operator?: boolean;
}) {
  const links = operator ? operatorLinks : riderLinks;
  return (
    <div className="app-shell bg-canvas">
      <a
        href="#main-content"
        className="bg-brand-strong fixed top-4 left-4 z-50 -translate-y-24 rounded-lg px-4 py-3 font-semibold text-white focus:translate-y-0"
      >
        Skip to main content
      </a>
      <header className="bg-surface sticky top-0 z-30 border-b">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-2 px-3 py-3 sm:gap-4 sm:px-6 lg:px-8">
          <Link
            href="/"
            className="flex min-h-11 items-center gap-2 font-semibold"
          >
            <span className="bg-brand-soft text-brand-soft-text grid size-9 place-items-center rounded-lg">
              <Activity aria-hidden="true" className="size-5" />
            </span>
            TransitPulse
            {operator ? (
              <span className="text-muted text-sm font-medium">Operator</span>
            ) : null}
          </Link>
          <nav
            aria-label={operator ? "Operator navigation" : "Rider navigation"}
            className="hidden items-center gap-1 lg:flex"
          >
            {links.map(({ href, label }) => (
              <Link
                className="text-muted hover:bg-surface-muted hover:text-text rounded-md px-3 py-2 text-sm font-medium"
                href={href}
                key={href}
              >
                {label}
              </Link>
            ))}
            <Link
              className="text-muted hover:bg-surface-muted hover:text-text rounded-md px-3 py-2 text-sm font-medium"
              href={operator ? "/" : "/operator"}
            >
              {operator ? "Rider view" : "Operator"}
            </Link>
          </nav>
          <div className="flex items-center gap-2">
            <ThemeSelect />
            <span className="text-muted grid size-11 place-items-center md:hidden">
              <Menu aria-hidden="true" className="size-5" />
            </span>
          </div>
        </div>
      </header>
      <NetworkStatusStrip />
      <main id="main-content" className="page-container">
        {children}
      </main>
      <footer className="text-muted mx-auto max-w-7xl border-t px-4 py-6 pb-24 text-sm sm:px-6 lg:px-8 lg:pb-6">
        Transit data provided by MassDOT/MBTA. TransitPulse is an independent
        project and is not affiliated with or endorsed by MBTA.{" "}
        <span className="mt-2 inline-flex flex-wrap gap-x-3 gap-y-2 sm:mt-0 sm:ml-2">
          <Link className="underline" href="/methodology">
            Methodology
          </Link>
          <Link className="underline" href="/data-sources">
            Data sources
          </Link>
          <Link className="underline" href="/privacy">
            Privacy
          </Link>
          <Link className="underline" href="/accessibility">
            Accessibility
          </Link>
        </span>
      </footer>
      <nav
        aria-label="Mobile navigation"
        className="bg-surface fixed inset-x-0 bottom-0 z-30 flex justify-around border-t pb-[env(safe-area-inset-bottom)] lg:hidden"
      >
        {links.map(({ href, label, icon: Icon }) => (
          <Link
            href={href}
            key={href}
            className="text-muted flex min-h-16 min-w-0 flex-1 flex-col items-center justify-center gap-1 px-1 text-xs font-medium"
          >
            <Icon aria-hidden="true" className="size-5" />
            {label}
          </Link>
        ))}
      </nav>
    </div>
  );
}

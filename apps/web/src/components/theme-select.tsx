"use client";

import { useSyncExternalStore } from "react";
import { MoonStar } from "lucide-react";
import { useTheme } from "next-themes";

const themes = ["system", "light", "dark"] as const;

export function ThemeSelect() {
  const mounted = useSyncExternalStore(
    () => () => undefined,
    () => true,
    () => false,
  );
  const { theme, setTheme } = useTheme();

  return (
    <label className="text-muted flex min-h-11 items-center gap-2 text-sm font-medium">
      <MoonStar aria-hidden="true" className="hidden size-4 sm:block" />
      <span className="sr-only">Color theme</span>
      <select
        aria-label="Color theme"
        className="border-border-strong bg-surface text-text min-h-11 rounded-lg border px-2 sm:px-3"
        disabled={!mounted}
        value={mounted ? theme : "system"}
        onChange={(event) => setTheme(event.target.value)}
      >
        {themes.map((item) => (
          <option key={item} value={item}>
            {item[0].toUpperCase() + item.slice(1)}
          </option>
        ))}
      </select>
    </label>
  );
}

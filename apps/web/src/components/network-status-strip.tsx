"use client";

import { CloudOff } from "lucide-react";
import { useEffect, useState } from "react";

export function NetworkStatusStrip() {
  const [online, setOnline] = useState(true);

  useEffect(() => {
    const update = () => setOnline(navigator.onLine);
    update();
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);

  if (online) return null;
  return (
    <div
      className="bg-status-offline-surface text-status-offline border-b px-4 py-3 text-sm"
      role="status"
      aria-live="polite"
    >
      <div className="mx-auto flex max-w-7xl items-center gap-2">
        <CloudOff aria-hidden="true" className="size-5 shrink-0" />
        <span>
          You are offline. Saved app pages may be available, but live transit
          data is not being shown.
        </span>
      </div>
    </div>
  );
}

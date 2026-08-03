"use client";

import { useEffect, useState } from "react";

export function PwaRegistration() {
  const [waitingWorker, setWaitingWorker] = useState<ServiceWorker | null>(
    null,
  );

  useEffect(() => {
    // Playwright runs several isolated pages concurrently; registering a worker
    // there can trigger a controller reload midway through an accessibility scan.
    if (!("serviceWorker" in navigator) || navigator.webdriver) return;

    let registration: ServiceWorkerRegistration | undefined;
    const showUpdate = () => setWaitingWorker(registration?.waiting ?? null);

    void navigator.serviceWorker
      .register("/sw.js")
      .then((nextRegistration) => {
        registration = nextRegistration;
        showUpdate();
        nextRegistration.addEventListener("updatefound", () => {
          nextRegistration.installing?.addEventListener("statechange", () => {
            if (nextRegistration.installing?.state === "installed")
              showUpdate();
          });
        });
      })
      .catch(() => {
        // The application continues normally when offline installation is unavailable.
      });

    const reloadForUpdate = () => window.location.reload();
    navigator.serviceWorker.addEventListener(
      "controllerchange",
      reloadForUpdate,
    );
    return () =>
      navigator.serviceWorker.removeEventListener(
        "controllerchange",
        reloadForUpdate,
      );
  }, []);

  if (!waitingWorker) return null;

  return (
    <div
      className="bg-surface-raised fixed inset-x-4 bottom-24 z-50 mx-auto flex max-w-xl items-center justify-between gap-3 rounded-lg border p-4 shadow-lg lg:bottom-6"
      role="status"
      aria-live="polite"
    >
      <p className="text-sm">A newer TransitPulse version is ready.</p>
      <button
        type="button"
        className="bg-brand-strong min-h-11 shrink-0 rounded-md px-4 text-sm font-semibold text-white"
        onClick={() => waitingWorker.postMessage({ type: "SKIP_WAITING" })}
      >
        Update now
      </button>
    </div>
  );
}

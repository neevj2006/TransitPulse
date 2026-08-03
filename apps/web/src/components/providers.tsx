"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { ThemeProvider } from "@/components/theme-provider";
import { PwaRegistration } from "@/components/pwa-registration";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { staleTime: 15_000, retry: 1 } },
      }),
  );
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        {children}
        <PwaRegistration />
      </QueryClientProvider>
    </ThemeProvider>
  );
}

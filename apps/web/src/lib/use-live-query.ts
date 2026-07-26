"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { connectLiveStream } from "@/lib/live-stream";

export function useLiveQuery<T>({
  key,
  fetcher,
  streamUrl,
}: {
  key: readonly unknown[];
  fetcher: () => Promise<T>;
  streamUrl?: string;
}) {
  const query = useQuery({ queryKey: key, queryFn: fetcher });
  const client = useQueryClient();
  useEffect(() => {
    if (!streamUrl) return;
    return connectLiveStream({
      url: streamUrl,
      onEvent: () => client.invalidateQueries({ queryKey: key }),
      onFallback: () => client.invalidateQueries({ queryKey: key }),
    });
  }, [client, key, streamUrl]);
  return query;
}

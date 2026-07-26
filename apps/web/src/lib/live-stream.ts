export type LiveStreamOptions = {
  url: string;
  onEvent: (event: MessageEvent<string>) => void;
  onFallback: () => Promise<void> | void;
  pollingIntervalMs?: number;
};

/** Uses SSE when available, then bounded polling after a disconnect. */
export function connectLiveStream({
  url,
  onEvent,
  onFallback,
  pollingIntervalMs = 30_000,
}: LiveStreamOptions): () => void {
  let timer: ReturnType<typeof setInterval> | undefined;
  const stream = new EventSource(url);
  const startFallback = () => {
    if (timer) return;
    void onFallback();
    timer = setInterval(() => void onFallback(), pollingIntervalMs);
  };
  stream.addEventListener("vehicle.changed", onEvent);
  stream.addEventListener("arrival.changed", onEvent);
  stream.addEventListener("alert.changed", onEvent);
  stream.addEventListener("error", startFallback);
  stream.addEventListener("open", () => {
    if (timer) clearInterval(timer);
    timer = undefined;
  });
  return () => {
    stream.close();
    if (timer) clearInterval(timer);
  };
}

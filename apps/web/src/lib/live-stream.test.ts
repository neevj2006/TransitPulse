import { expect, it, vi } from "vitest";

import { connectLiveStream } from "./live-stream";

class FakeEventSource extends EventTarget {
  static latest: FakeEventSource | undefined;
  close = vi.fn();
  constructor(url: string) {
    super();
    void url;
    FakeEventSource.latest = this;
  }
}

it("falls back to bounded polling when the stream errors", () => {
  vi.useFakeTimers();
  vi.stubGlobal("EventSource", FakeEventSource);
  const fallback = vi.fn();
  const dispose = connectLiveStream({
    url: "/events",
    onEvent: vi.fn(),
    onFallback: fallback,
    pollingIntervalMs: 1000,
  });
  FakeEventSource.latest?.dispatchEvent(new Event("error"));
  expect(fallback).toHaveBeenCalledTimes(1);
  vi.advanceTimersByTime(2000);
  expect(fallback).toHaveBeenCalledTimes(3);
  dispose();
  expect(FakeEventSource.latest?.close).toHaveBeenCalledOnce();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

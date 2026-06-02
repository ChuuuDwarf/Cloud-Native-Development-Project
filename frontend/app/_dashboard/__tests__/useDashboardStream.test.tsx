import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useDashboardStream } from "../useDashboardStream";

type Listener = () => void;

class FakeEventSource {
  static instances: FakeEventSource[] = [];
  url: string;
  withCredentials: boolean;
  listeners: Record<string, Listener> = {};
  onmessage: Listener | null = null;
  onerror: (() => void) | null = null;
  closed = false;

  constructor(url: string, init?: { withCredentials?: boolean }) {
    this.url = url;
    this.withCredentials = Boolean(init?.withCredentials);
    FakeEventSource.instances.push(this);
  }

  addEventListener(name: string, fn: Listener) {
    this.listeners[name] = fn;
  }

  close() {
    this.closed = true;
  }
}

function makeClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

describe("useDashboardStream", () => {
  beforeEach(() => {
    FakeEventSource.instances = [];
    vi.stubGlobal("EventSource", FakeEventSource as unknown as typeof EventSource);
  });
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  function setup() {
    const client = makeClient();
    const invalidateSpy = vi.spyOn(client, "invalidateQueries");
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    );
    const view = renderHook(() => useDashboardStream(), { wrapper });
    return { invalidateSpy, view };
  }

  it("opens an EventSource against the dashboard stream with credentials", () => {
    setup();
    const es = FakeEventSource.instances[0];
    expect(es).toBeDefined();
    expect(es.url).toContain("/dashboard/stream");
    expect(es.withCredentials).toBe(true);
  });

  it("invalidates the dashboard query on a named event and onmessage", () => {
    const { invalidateSpy } = setup();
    const es = FakeEventSource.instances[0];

    es.listeners.dashboard();
    es.onmessage?.();

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["dashboard"] });
    expect(invalidateSpy).toHaveBeenCalledTimes(2);
  });

  it("closes the connection on unmount", () => {
    const { view } = setup();
    const es = FakeEventSource.instances[0];
    view.unmount();
    expect(es.closed).toBe(true);
  });

  it("does not throw when EventSource construction fails", () => {
    vi.stubGlobal(
      "EventSource",
      class {
        constructor() {
          throw new Error("blocked");
        }
      } as unknown as typeof EventSource
    );
    expect(() => setup()).not.toThrow();
  });
});

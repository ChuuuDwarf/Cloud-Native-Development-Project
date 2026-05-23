import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import UserSwitcher, {
  authHeaders,
  getCurrentUserId,
} from "@/components/UserSwitcher";

describe("UserSwitcher helpers", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns the default lab user while rendering on the server", () => {
    expect(getCurrentUserId()).toBe("u-lab-a");
    expect(authHeaders()).toEqual({ "X-User-Id": "u-lab-a" });
  });

  it("prefers an explicit user id for auth headers", () => {
    expect(authHeaders("u-admin")).toEqual({ "X-User-Id": "u-admin" });
  });

  it("reads the browser localStorage user id when available", () => {
    vi.stubGlobal("window", {
      localStorage: {
        getItem: vi.fn(() => "u-supervisor-b"),
      },
    });

    expect(getCurrentUserId()).toBe("u-supervisor-b");
    expect(authHeaders()).toEqual({ "X-User-Id": "u-supervisor-b" });
  });

  it("falls back to the default user when localStorage has no value", () => {
    vi.stubGlobal("window", {
      localStorage: {
        getItem: vi.fn(() => null),
      },
    });

    expect(getCurrentUserId()).toBe("u-lab-a");
  });
});

describe("UserSwitcher component", () => {
  it("server-renders an empty select and disconnected badge before data loads", () => {
    const html = renderToStaticMarkup(<UserSwitcher />);

    expect(html).toContain("<select");
    expect(html).toContain("未連線");
  });
});

import { afterEach, describe, expect, it, vi } from "vitest";

import { getErrorMessage, logClientError } from "./error";

describe("error helpers", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("getErrorMessage 會優先回傳 Error message", () => {
    expect(getErrorMessage(new Error("後端錯誤"), "預設錯誤")).toBe("後端錯誤");
  });

  it("getErrorMessage 會處理字串錯誤", () => {
    expect(getErrorMessage("字串錯誤", "預設錯誤")).toBe("字串錯誤");
  });

  it("getErrorMessage 遇到空字串或未知錯誤時回傳 fallback", () => {
    expect(getErrorMessage("", "預設錯誤")).toBe("預設錯誤");
    expect(getErrorMessage(new Error("   "), "預設錯誤")).toBe("預設錯誤");
    expect(getErrorMessage(null, "預設錯誤")).toBe("預設錯誤");
    expect(getErrorMessage(undefined, "預設錯誤")).toBe("預設錯誤");
    expect(getErrorMessage({ detail: "不會直接解析物件" }, "預設錯誤")).toBe("預設錯誤");
  });

  it("logClientError 在非 production 會輸出 console.error", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    vi.stubEnv("NODE_ENV", "test");

    const error = new Error("測試錯誤");
    logClientError("load failed", error);

    expect(spy).toHaveBeenCalledWith("load failed:", error);
  });

  it("logClientError 在 production 不會輸出 console.error", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => undefined);
    vi.stubEnv("NODE_ENV", "production");

    logClientError("load failed", new Error("測試錯誤"));

    expect(spy).not.toHaveBeenCalled();
  });
});

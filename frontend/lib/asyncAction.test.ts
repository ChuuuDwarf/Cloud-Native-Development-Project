import { describe, expect, it, vi } from "vitest";

import { runClientAction } from "./asyncAction";

describe("runClientAction", () => {
  it("成功時會清空錯誤、設定 loading/submitting，並回傳 action 結果", async () => {
    const setError = vi.fn();
    const setSuccessMessage = vi.fn();
    const setLoading = vi.fn();
    const setSubmitting = vi.fn();

    const result = await runClientAction(
      async () => {
        return { ok: true };
      },
      {
        fallbackError: "操作失敗",
        successMessage: "操作成功",
        setError,
        setSuccessMessage,
        setLoading,
        setSubmitting,
      }
    );

    expect(result).toEqual({ ok: true });
    expect(setLoading).toHaveBeenNthCalledWith(1, true);
    expect(setSubmitting).toHaveBeenNthCalledWith(1, true);
    expect(setError).toHaveBeenCalledWith("");
    expect(setSuccessMessage).toHaveBeenNthCalledWith(1, "");
    expect(setSuccessMessage).toHaveBeenNthCalledWith(2, "操作成功");
    expect(setLoading).toHaveBeenLastCalledWith(false);
    expect(setSubmitting).toHaveBeenLastCalledWith(false);
  });

  it("成功但沒有 successMessage 時不會設定成功訊息", async () => {
    const setError = vi.fn();
    const setSuccessMessage = vi.fn();

    const result = await runClientAction(async () => "done", {
      fallbackError: "操作失敗",
      setError,
      setSuccessMessage,
    });

    expect(result).toBe("done");
    expect(setSuccessMessage).toHaveBeenCalledTimes(1);
    expect(setSuccessMessage).toHaveBeenCalledWith("");
  });

  it("失敗時會回傳 null，並把錯誤訊息寫入 setError", async () => {
    const setError = vi.fn();
    const setSuccessMessage = vi.fn();
    const setLoading = vi.fn();
    const setSubmitting = vi.fn();
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);

    const result = await runClientAction(
      async () => {
        throw new Error("API 掛了");
      },
      {
        fallbackError: "操作失敗",
        context: "submit failed",
        setError,
        setSuccessMessage,
        setLoading,
        setSubmitting,
      }
    );

    expect(result).toBeNull();
    expect(setError).toHaveBeenLastCalledWith("API 掛了");
    expect(setLoading).toHaveBeenLastCalledWith(false);
    expect(setSubmitting).toHaveBeenLastCalledWith(false);
    expect(consoleSpy).toHaveBeenCalled();

    consoleSpy.mockRestore();
  });

  it("失敗但錯誤沒有 message 時會使用 fallbackError", async () => {
    const setError = vi.fn();
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => undefined);

    const result = await runClientAction(
      async () => {
        throw "";
      },
      {
        fallbackError: "預設錯誤",
        setError,
      }
    );

    expect(result).toBeNull();
    expect(setError).toHaveBeenCalledWith("預設錯誤");

    consoleSpy.mockRestore();
  });
});

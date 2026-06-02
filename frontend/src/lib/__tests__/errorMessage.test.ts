import { describe, expect, it } from "vitest";
import { errorMessage } from "@/lib/errorMessage";

describe("errorMessage", () => {
  it("prefers backend business error messages", () => {
    expect(
      errorMessage({
        response: {
          data: {
            error: {
              code: "VALIDATION_ERROR",
              message: "數據完整性尚未驗證",
            },
          },
        },
      })
    ).toBe("數據完整性尚未驗證");
  });

  it("falls back to Error.message, then the generic offline hint", () => {
    expect(errorMessage(new Error("Request failed"))).toBe("Request failed");
    expect(errorMessage({})).toBe("操作失敗，請確認後端是否啟動");
  });
});

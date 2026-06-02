import { describe, expect, it } from "vitest";

import type { CurrentUser } from "../types";
import {
  getRoleLabel,
  isFactoryUser,
  isLabUser,
  isSystemAdmin,
} from "./sampleDisplay";

function user(overrides: Partial<CurrentUser> = {}): CurrentUser {
  return { id: "u", name: "n", role: "lab_engineer", department: "Lab A", ...overrides };
}

describe("sampleDisplay role helpers", () => {
  it("identifies system admins", () => {
    expect(isSystemAdmin(user({ role: "system_admin" }))).toBe(true);
    expect(isSystemAdmin(user({ role: "lab_engineer" }))).toBe(false);
  });

  it("identifies lab users (engineer + supervisor)", () => {
    expect(isLabUser(user({ role: "lab_engineer" }))).toBe(true);
    expect(isLabUser(user({ role: "lab_supervisor" }))).toBe(true);
    expect(isLabUser(user({ role: "plant_user" }))).toBe(false);
  });

  it("identifies factory users", () => {
    expect(isFactoryUser(user({ role: "plant_user" }))).toBe(true);
    expect(isFactoryUser(user({ role: "system_admin" }))).toBe(false);
  });

  describe("getRoleLabel", () => {
    it("prefers an explicit role_name", () => {
      expect(getRoleLabel(user({ role_name: "客製名稱" }))).toBe("客製名稱");
    });

    it("maps known roles to Chinese labels", () => {
      expect(getRoleLabel(user({ role: "system_admin" }))).toBe("系統管理者");
      expect(getRoleLabel(user({ role: "lab_supervisor" }))).toBe("實驗室主管");
      expect(getRoleLabel(user({ role: "lab_engineer" }))).toBe("實驗室人員");
      expect(getRoleLabel(user({ role: "plant_user" }))).toBe("廠區使用者");
    });

    it("falls back to the raw role for unknown roles", () => {
      expect(getRoleLabel(user({ role: "weird_role" }))).toBe("weird_role");
      // role is `??`-coalesced, so an empty-string role passes through as-is
      // (only null/undefined would reach the 未知角色 default).
      expect(getRoleLabel(user({ role: undefined as never }))).toBe("未知角色");
    });
  });
});

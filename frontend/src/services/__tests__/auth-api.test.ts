import { describe, it, expect, vi, beforeEach } from "vitest";

// Typed mock for httpClient. Each test asserts on these spies.
const getMock = vi.fn();
const postMock = vi.fn();
vi.mock("@/api/httpClient", () => ({
  httpClient: {
    get: (...args: unknown[]) => getMock(...args),
    post: (...args: unknown[]) => postMock(...args),
  },
}));

import { authApi } from "@/services/auth-api";

describe("authApi", () => {
  beforeEach(() => {
    getMock.mockReset();
    postMock.mockReset();
  });

  it("login() POSTs /auth/login and unwraps data from ApiResponse", async () => {
    const payload = { email: "a@b.c", password: "x" };
    const fakeLoginData = {
      userId: "u-1",
      name: "A",
      email: "a@b.c",
      role: "system_admin",
      permissions: ["*"],
    };
    postMock.mockResolvedValue({
      data: { data: fakeLoginData, message: "success" },
    });

    const result = await authApi.login(payload);

    expect(postMock).toHaveBeenCalledTimes(1);
    expect(postMock).toHaveBeenCalledWith("/auth/login", payload);
    expect(result).toEqual(fakeLoginData);
  });

  it("me() GETs /me and unwraps data", async () => {
    const me = {
      id: "u-1",
      name: "A",
      email: "a@b.c",
      role: "system_admin",
      permissions: ["*"],
      labId: null,
      departmentId: null,
    };
    getMock.mockResolvedValue({ data: { data: me, message: "success" } });

    const result = await authApi.me();

    expect(getMock).toHaveBeenCalledTimes(1);
    expect(getMock).toHaveBeenCalledWith("/me");
    expect(result).toEqual(me);
  });

  it("logout() POSTs /auth/logout", async () => {
    postMock.mockResolvedValue({ data: {} });

    await authApi.logout();

    expect(postMock).toHaveBeenCalledTimes(1);
    expect(postMock).toHaveBeenCalledWith("/auth/logout");
  });

  it("login() propagates network errors so AuthContext can surface them", async () => {
    const err = { response: { status: 401 } };
    postMock.mockRejectedValue(err);

    await expect(authApi.login({ email: "x", password: "y" })).rejects.toEqual(err);
  });
});

import { describe, it, expect, vi, beforeEach } from "vitest";

const getMock = vi.fn();
const postMock = vi.fn();
const patchMock = vi.fn();
vi.mock("@/api/httpClient", () => ({
  httpClient: {
    get: (...args: unknown[]) => getMock(...args),
    post: (...args: unknown[]) => postMock(...args),
    patch: (...args: unknown[]) => patchMock(...args),
  },
}));

import { userApi } from "@/services/user-api";

const fakeUser = {
  id: "u-1",
  email: "a@b.c",
  name: "A",
  departmentId: null,
  labId: null,
  status: "active" as const,
  isActive: true,
  roles: [],
  createdAt: "2026-05-01T00:00:00Z",
  updatedAt: "2026-05-01T00:00:00Z",
};

describe("userApi", () => {
  beforeEach(() => {
    getMock.mockReset();
    postMock.mockReset();
    patchMock.mockReset();
  });

  it("list() GETs /users with the query as params and returns PageResponse without unwrapping", async () => {
    const page = {
      items: [fakeUser],
      page: 1,
      pageSize: 20,
      total: 1,
    };
    // userApi.list returns res.data (PageResponse is the whole body, no `data` wrapper)
    getMock.mockResolvedValue({ data: page });

    const result = await userApi.list({ keyword: "admin" });

    expect(getMock).toHaveBeenCalledTimes(1);
    expect(getMock).toHaveBeenCalledWith("/users", {
      params: { keyword: "admin" },
    });
    expect(result).toEqual(page);
  });

  it("list() with no args sends an empty params object", async () => {
    getMock.mockResolvedValue({
      data: { items: [], page: 1, pageSize: 20, total: 0 },
    });

    await userApi.list();

    expect(getMock).toHaveBeenCalledWith("/users", { params: {} });
  });

  it("getById() GETs /users/:id and unwraps data", async () => {
    getMock.mockResolvedValue({
      data: { data: fakeUser, message: "success" },
    });

    const result = await userApi.getById("u-1");

    expect(getMock).toHaveBeenCalledWith("/users/u-1");
    expect(result).toEqual(fakeUser);
  });

  it("create() POSTs /users and unwraps data", async () => {
    const payload = {
      email: "n@b.c",
      name: "N",
      password: "Password1",
    };
    postMock.mockResolvedValue({
      data: { data: fakeUser, message: "success" },
    });

    const result = await userApi.create(payload);

    expect(postMock).toHaveBeenCalledWith("/users", payload);
    expect(result).toEqual(fakeUser);
  });

  it("update() PATCHes /users/:id and unwraps data", async () => {
    patchMock.mockResolvedValue({
      data: { data: fakeUser, message: "success" },
    });

    const result = await userApi.update("u-1", { name: "Renamed" });

    expect(patchMock).toHaveBeenCalledWith("/users/u-1", { name: "Renamed" });
    expect(result).toEqual(fakeUser);
  });
});

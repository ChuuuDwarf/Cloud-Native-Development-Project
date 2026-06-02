import { beforeEach, describe, expect, it, vi } from "vitest";

const { getMock, postMock, patchMock } = vi.hoisted(() => ({
  getMock: vi.fn(),
  postMock: vi.fn(),
  patchMock: vi.fn(),
}));

vi.mock("@/api/httpClient", () => ({
  httpClient: {
    get: getMock,
    post: postMock,
    patch: patchMock,
  },
}));

import { issueApi } from "@/services/issue-api";
import { notificationApi } from "@/services/notification-api";

describe("issueApi", () => {
  beforeEach(() => {
    getMock.mockReset();
    postMock.mockReset();
    patchMock.mockReset();
  });

  it("list() returns the page response and forwards query params", async () => {
    const page = { items: [{ id: "I-1" }], page: 1, pageSize: 20, total: 1 };
    const query = { status: "open", page: 1 };
    getMock.mockResolvedValue({ data: page });

    await expect(issueApi.list(query as never)).resolves.toEqual(page);

    expect(getMock).toHaveBeenCalledWith("/issues", { params: query });
  });

  it("getById(), create(), update(), and listAcknowledgements() unwrap data", async () => {
    const issue = { id: "I-1" };
    const acknowledgement = { id: "A-1" };
    getMock
      .mockResolvedValueOnce({ data: { data: issue } })
      .mockResolvedValueOnce({ data: { data: [acknowledgement] } });
    postMock.mockResolvedValue({ data: { data: issue } });
    patchMock.mockResolvedValue({ data: { data: issue } });

    await expect(issueApi.getById("I-1")).resolves.toEqual(issue);
    await expect(issueApi.create({ title: "bad" } as never)).resolves.toEqual(issue);
    await expect(issueApi.update("I-1", { status: "closed" } as never)).resolves.toEqual(issue);
    await expect(issueApi.listAcknowledgements("I-1")).resolves.toEqual([acknowledgement]);

    expect(getMock).toHaveBeenNthCalledWith(1, "/issues/I-1");
    expect(postMock).toHaveBeenCalledWith("/issues", { title: "bad" });
    expect(patchMock).toHaveBeenCalledWith("/issues/I-1", { status: "closed" });
    expect(getMock).toHaveBeenNthCalledWith(2, "/issues/I-1/acknowledgements");
  });
});

describe("notificationApi", () => {
  beforeEach(() => {
    getMock.mockReset();
    postMock.mockReset();
    patchMock.mockReset();
  });

  it("list() returns the page response and forwards query params", async () => {
    const page = { items: [{ id: "N-1" }], page: 1, pageSize: 20, total: 1 };
    const query = { unreadOnly: true, page: 1 };
    getMock.mockResolvedValue({ data: page });

    await expect(notificationApi.list(query as never)).resolves.toEqual(page);

    expect(getMock).toHaveBeenCalledWith("/notifications", { params: query });
  });

  it("getById() and markRead() unwrap data", async () => {
    const notification = { id: "N-1" };
    const result = { updated: 1 };
    getMock.mockResolvedValue({ data: { data: notification } });
    postMock.mockResolvedValue({ data: { data: result } });

    await expect(notificationApi.getById("N-1")).resolves.toEqual(notification);
    await expect(notificationApi.markRead({ ids: ["N-1"] } as never)).resolves.toEqual(result);

    expect(getMock).toHaveBeenCalledWith("/notifications/N-1");
    expect(postMock).toHaveBeenCalledWith("/notifications/actions", { ids: ["N-1"] });
  });
});

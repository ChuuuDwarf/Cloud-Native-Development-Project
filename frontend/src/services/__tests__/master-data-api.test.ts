import { describe, it, expect, vi, beforeEach } from "vitest";

const getMock = vi.fn();
vi.mock("@/api/httpClient", () => ({
  httpClient: {
    get: (...args: unknown[]) => getMock(...args),
  },
}));

import { masterDataApi } from "@/services/master-data-api";

describe("masterDataApi", () => {
  beforeEach(() => {
    getMock.mockReset();
  });

  it("fetch() GETs /master-data and unwraps data", async () => {
    const payload = {
      roles: [{ id: "r-1", name: "system_admin", description: "", permissions: ["*"] }],
      permissions: [],
      labs: [],
      departments: [],
      storageLocations: [],
      experimentItems: [],
      orderStatuses: ["draft"],
      wipStatuses: [],
      machineStatuses: [],
      reportStatuses: [],
      issueStatuses: [],
      issueTypes: [],
      notificationStatuses: [],
      userStatuses: [],
      severities: ["low", "medium", "high", "critical"],
    };
    getMock.mockResolvedValue({ data: { data: payload, message: "success" } });

    const result = await masterDataApi.fetch();

    expect(getMock).toHaveBeenCalledTimes(1);
    expect(getMock).toHaveBeenCalledWith("/master-data");
    expect(result).toEqual(payload);
  });
});

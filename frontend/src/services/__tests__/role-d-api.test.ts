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

import { closuresApi } from "@/services/closures-api";
import { dashboardApi } from "@/services/dashboard-api";
import { dispatchesApi } from "@/services/dispatches-api";
import { experimentsApi } from "@/services/experiments-api";
import { machinesApi } from "@/services/machines-api";
import { recipesApi } from "@/services/recipes-api";

describe("Role D service API wrappers", () => {
  beforeEach(() => {
    getMock.mockReset();
    postMock.mockReset();
    patchMock.mockReset();
  });

  it("closuresApi maps list, storage filters, and action endpoints", async () => {
    const closure = { orderId: "O-1" };
    const storage = { storageId: "S-1" };
    getMock
      .mockResolvedValueOnce({ data: { items: [closure] } })
      .mockResolvedValueOnce({ data: { items: [storage] } })
      .mockResolvedValueOnce({ data: { items: [storage] } });
    postMock
      .mockResolvedValueOnce({ data: { data: closure } })
      .mockResolvedValueOnce({ data: { data: storage } })
      .mockResolvedValueOnce({ data: { data: storage } })
      .mockResolvedValueOnce({ data: { data: closure } });

    await expect(closuresApi.list()).resolves.toEqual([closure]);
    await expect(closuresApi.listStorage()).resolves.toEqual([storage]);
    await expect(closuresApi.listStorage("已入庫")).resolves.toEqual([storage]);
    await expect(closuresApi.toPickup("O-1")).resolves.toEqual(closure);
    await expect(closuresApi.inbound("O-1", { operator: "A" })).resolves.toEqual(storage);
    await expect(closuresApi.outbound("O-1", { note: "done" })).resolves.toEqual(storage);
    await expect(closuresApi.close("O-1", { operator: "B" })).resolves.toEqual(closure);

    expect(getMock).toHaveBeenNthCalledWith(1, "/closures");
    expect(getMock).toHaveBeenNthCalledWith(2, "/closures/storage", undefined);
    expect(getMock).toHaveBeenNthCalledWith(3, "/closures/storage", {
      params: { status: "已入庫" },
    });
    expect(postMock).toHaveBeenNthCalledWith(1, "/closures/O-1/to-pickup");
    expect(postMock).toHaveBeenNthCalledWith(2, "/closures/O-1/inbound", { operator: "A" });
    expect(postMock).toHaveBeenNthCalledWith(3, "/closures/O-1/outbound", { note: "done" });
    expect(postMock).toHaveBeenNthCalledWith(4, "/closures/O-1/close", { operator: "B" });
  });

  it("dispatchesApi maps list, create, suggest, replan, and assign", async () => {
    const dispatch = { dispatchId: "D-1" };
    const createPayload = { wipId: "WIP-1", machineId: "M-1" };
    const assignPayload = { machineId: "M-2" };
    getMock.mockResolvedValue({ data: { items: [dispatch] } });
    postMock
      .mockResolvedValueOnce({ data: { data: dispatch } })
      .mockResolvedValueOnce({ data: { data: [dispatch] } })
      .mockResolvedValueOnce({ data: { data: [dispatch] } })
      .mockResolvedValueOnce({ data: { data: dispatch } });

    await expect(dispatchesApi.list()).resolves.toEqual([dispatch]);
    await expect(dispatchesApi.create(createPayload as never)).resolves.toEqual(dispatch);
    await expect(dispatchesApi.suggest("balanced" as never)).resolves.toEqual([dispatch]);
    await expect(dispatchesApi.replan("urgent", "fastest" as never)).resolves.toEqual([dispatch]);
    await expect(dispatchesApi.assign("D-1", assignPayload as never)).resolves.toEqual(dispatch);

    expect(getMock).toHaveBeenCalledWith("/dispatches");
    expect(postMock).toHaveBeenNthCalledWith(1, "/dispatches", createPayload);
    expect(postMock).toHaveBeenNthCalledWith(2, "/dispatches/suggest", { strategy: "balanced" });
    expect(postMock).toHaveBeenNthCalledWith(3, "/dispatches/replan", {
      reason: "urgent",
      strategy: "fastest",
    });
    expect(postMock).toHaveBeenNthCalledWith(4, "/dispatches/D-1/assign", assignPayload);
  });

  it("experimentsApi maps list and all action endpoints", async () => {
    const wip = { wipId: "WIP-1" };
    const operators = [{ name: "Op", role: "lab_engineer" }];
    getMock
      .mockResolvedValueOnce({ data: { items: [wip] } })
      .mockResolvedValueOnce({ data: { data: operators } });
    postMock.mockResolvedValue({ data: { data: wip } });
    patchMock.mockResolvedValue({ data: { data: wip } });

    await expect(experimentsApi.list()).resolves.toEqual([wip]);
    await expect(experimentsApi.getOperators("WIP-1")).resolves.toEqual(operators);
    await expect(
      experimentsApi.checkIn("WIP-1", { operator: "Op", machineId: "M-1", recipe: "R" })
    ).resolves.toEqual(wip);
    await expect(experimentsApi.checkOut("WIP-1", { operator: "Op" })).resolves.toEqual(wip);
    await expect(experimentsApi.updateProgress("WIP-1", 45)).resolves.toEqual(wip);
    await expect(
      experimentsApi.uploadResult("WIP-1", { note: "ok", dataVerified: true })
    ).resolves.toEqual(wip);
    await expect(experimentsApi.verify("WIP-1", { operator: "Lead" })).resolves.toEqual(wip);
    await expect(experimentsApi.confirm("WIP-1", { operator: "Lead" })).resolves.toEqual(wip);
    await expect(experimentsApi.abortRequest("WIP-1", "bad sample")).resolves.toEqual(wip);
    await expect(
      experimentsApi.abortReview("WIP-1", { approve: true, note: "ok" })
    ).resolves.toEqual(wip);
    await expect(experimentsApi.machineSignal("WIP-1")).resolves.toEqual(wip);

    expect(getMock).toHaveBeenNthCalledWith(1, "/experiment-runs");
    expect(getMock).toHaveBeenNthCalledWith(2, "/experiment-runs/WIP-1/operators");
    expect(postMock).toHaveBeenNthCalledWith(1, "/experiment-runs/WIP-1/check-in", {
      operator: "Op",
      machineId: "M-1",
      recipe: "R",
    });
    expect(postMock).toHaveBeenNthCalledWith(2, "/experiment-runs/WIP-1/check-out", {
      operator: "Op",
    });
    expect(patchMock).toHaveBeenCalledWith("/experiment-runs/WIP-1/progress", { progress: 45 });
    expect(postMock).toHaveBeenNthCalledWith(3, "/experiment-runs/WIP-1/result", {
      note: "ok",
      dataVerified: true,
    });
    expect(postMock).toHaveBeenNthCalledWith(4, "/experiment-runs/WIP-1/verify", {
      operator: "Lead",
    });
    expect(postMock).toHaveBeenNthCalledWith(5, "/experiment-runs/WIP-1/confirm", {
      operator: "Lead",
    });
    expect(postMock).toHaveBeenNthCalledWith(6, "/experiment-runs/WIP-1/abort-request", {
      reason: "bad sample",
    });
    expect(postMock).toHaveBeenNthCalledWith(7, "/experiment-runs/WIP-1/abort-review", {
      approve: true,
      note: "ok",
    });
    expect(postMock).toHaveBeenNthCalledWith(8, "/experiment-runs/WIP-1/machine-signal");
  });

  it("dashboardApi unwraps the dashboard snapshot", async () => {
    const snapshot = { kpis: [] };
    getMock.mockResolvedValue({ data: { data: snapshot } });

    await expect(dashboardApi.getSnapshot()).resolves.toEqual(snapshot);

    expect(getMock).toHaveBeenCalledWith("/dashboard");
  });

  it("machinesApi maps list, create, update, and status updates", async () => {
    const machine = { machineId: "M-1" };
    const payload = { name: "M", labId: "L-1", status: "idle" };
    getMock.mockResolvedValue({ data: { items: [machine] } });
    postMock.mockResolvedValue({ data: { data: machine } });
    patchMock.mockResolvedValue({ data: { data: machine } });

    await expect(machinesApi.list()).resolves.toEqual([machine]);
    await expect(machinesApi.create(payload as never)).resolves.toEqual(machine);
    await expect(machinesApi.update("M-1", payload as never)).resolves.toEqual(machine);
    await expect(machinesApi.updateStatus("M-1", "maintenance" as never)).resolves.toEqual(machine);

    expect(getMock).toHaveBeenCalledWith("/machines");
    expect(postMock).toHaveBeenCalledWith("/machines", payload);
    expect(patchMock).toHaveBeenNthCalledWith(1, "/machines/M-1", payload);
    expect(patchMock).toHaveBeenNthCalledWith(2, "/machines/M-1/status", {
      status: "maintenance",
    });
  });

  it("recipesApi maps list, create, and update", async () => {
    const recipe = { recipeId: "R-1" };
    const payload = { name: "Recipe", machineId: "M-1" };
    getMock.mockResolvedValue({ data: { items: [recipe] } });
    postMock.mockResolvedValue({ data: { data: recipe } });
    patchMock.mockResolvedValue({ data: { data: recipe } });

    await expect(recipesApi.list()).resolves.toEqual([recipe]);
    await expect(recipesApi.create(payload as never)).resolves.toEqual(recipe);
    await expect(recipesApi.update("R-1", payload as never)).resolves.toEqual(recipe);

    expect(getMock).toHaveBeenCalledWith("/recipes");
    expect(postMock).toHaveBeenCalledWith("/recipes", payload);
    expect(patchMock).toHaveBeenCalledWith("/recipes/R-1", payload);
  });
});

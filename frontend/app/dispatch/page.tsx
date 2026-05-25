"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import KpiCard from "@/components/ui/KpiCard";
import { machinesApi } from "@/services/machines-api";
import { recipesApi } from "@/services/recipes-api";
import {
  dispatchesApi,
  type CreateDispatchPayload,
  type Strategy,
} from "@/services/dispatches-api";
import DispatchForm from "./DispatchForm";
import DispatchTable from "./DispatchTable";
import DispatchAssignPanel from "./DispatchAssignPanel";
import StrategyBar, { STRATEGIES } from "./StrategyBar";

const BLOCKED = ["故障中", "保養中", "停用"];

function toDateTimeLocal(value?: string | null) {
  if (!value) return "";
  return value.replace(" ", "T").slice(0, 16);
}

function toApiDateTime(value: string) {
  return value.replace("T", " ");
}

export default function DispatchPage() {
  const queryClient = useQueryClient();
  const [strategy, setStrategy] = useState<Strategy>("FIFO");
  const [activeDispatchId, setActiveDispatchId] = useState("");
  const [scheduleDrafts, setScheduleDrafts] = useState<
    Record<string, { scheduledStart?: string; scheduledEnd?: string }>
  >({});

  const machinesQuery = useQuery({
    queryKey: ["machines"],
    queryFn: machinesApi.list,
  });
  const recipesQuery = useQuery({
    queryKey: ["recipes"],
    queryFn: recipesApi.list,
  });
  const dispatchesQuery = useQuery({
    queryKey: ["dispatches"],
    queryFn: dispatchesApi.list,
  });

  const machines = useMemo(
    () => machinesQuery.data ?? [],
    [machinesQuery.data],
  );
  const recipes = useMemo(() => recipesQuery.data ?? [], [recipesQuery.data]);
  const dispatches = useMemo(
    () => dispatchesQuery.data ?? [],
    [dispatchesQuery.data],
  );

  const invalidateDispatches = () =>
    queryClient.invalidateQueries({ queryKey: ["dispatches"] });

  const create = useMutation({
    mutationFn: (payload: CreateDispatchPayload) =>
      dispatchesApi.create(payload),
    onSuccess: invalidateDispatches,
  });

  const suggest = useMutation({
    mutationFn: () => dispatchesApi.suggest(strategy),
    onSuccess: invalidateDispatches,
  });

  const replan = useMutation({
    mutationFn: (vars: { reason: string; strategy: Strategy }) =>
      dispatchesApi.replan(vars.reason, vars.strategy),
    onSuccess: invalidateDispatches,
  });

  const assign = useMutation({
    mutationFn: (vars: {
      dispatchId: string;
      machineId: string;
      recipeId: string;
      scheduledStart: string;
      scheduledEnd: string;
    }) =>
      dispatchesApi.assign(vars.dispatchId, {
        machineId: vars.machineId,
        recipeId: vars.recipeId,
        scheduledStart: toApiDateTime(vars.scheduledStart),
        scheduledEnd: toApiDateTime(vars.scheduledEnd),
      }),
    onSuccess: invalidateDispatches,
  });

  const experimentItems = useMemo(
    () =>
      Array.from(new Set(machines.flatMap((machine) => machine.supportedItems))),
    [machines],
  );

  const activeDispatch =
    dispatches.find((dispatch) => dispatch.dispatchId === activeDispatchId) ??
    dispatches[0];
  const activeScheduleDraft = activeDispatch
    ? scheduleDrafts[activeDispatch.dispatchId]
    : undefined;
  const scheduledStart =
    activeScheduleDraft?.scheduledStart ??
    toDateTimeLocal(activeDispatch?.scheduledStart);
  const scheduledEnd =
    activeScheduleDraft?.scheduledEnd ??
    toDateTimeLocal(activeDispatch?.scheduledEnd);

  function updateScheduleDraft(
    field: "scheduledStart" | "scheduledEnd",
    value: string,
  ) {
    if (!activeDispatch) return;
    setScheduleDrafts((current) => ({
      ...current,
      [activeDispatch.dispatchId]: {
        ...current[activeDispatch.dispatchId],
        [field]: value,
      },
    }));
  }

  function applySuggestedSchedule() {
    if (!activeDispatch) return;
    setScheduleDrafts((current) => ({
      ...current,
      [activeDispatch.dispatchId]: {
        scheduledStart: toDateTimeLocal(activeDispatch.scheduledStart),
        scheduledEnd: toDateTimeLocal(activeDispatch.scheduledEnd),
      },
    }));
  }

  const assignableMachines = useMemo(() => {
    if (!activeDispatch) return [];
    return machines.filter(
      (machine) =>
        machine.supportedItems.includes(activeDispatch.experimentItem) &&
        !BLOCKED.includes(machine.status),
    );
  }, [activeDispatch, machines]);

  const selectedMachineId =
    activeDispatch?.suggestedMachineId &&
    assignableMachines.some(
      (machine) => machine.machineId === activeDispatch.suggestedMachineId,
    )
      ? activeDispatch.suggestedMachineId
      : assignableMachines[0]?.machineId;

  const assignableRecipes = useMemo(() => {
    if (!activeDispatch || !selectedMachineId) return [];
    return recipes.filter(
      (recipe) =>
        recipe.experimentItem === activeDispatch.experimentItem &&
        recipe.machineIds.includes(selectedMachineId),
    );
  }, [activeDispatch, recipes, selectedMachineId]);

  const summary = useMemo(
    () => ({
      pending: dispatches.filter((dispatch) => dispatch.status === "待派工")
        .length,
      scheduling: dispatches.filter((dispatch) => dispatch.status === "排程中")
        .length,
      ready: dispatches.filter((dispatch) => dispatch.status === "待上機")
        .length,
      blockedMachines: machines.filter((machine) =>
        BLOCKED.includes(machine.status),
      ).length,
    }),
    [dispatches, machines],
  );

  function handleReplan(reason: string, recommendedStrategy: Strategy) {
    setStrategy(recommendedStrategy);
    replan.mutate({ reason, strategy: recommendedStrategy });
  }

  function handleAssign() {
    if (!activeDispatch || !selectedMachineId || !assignableRecipes[0]) return;
    assign.mutate({
      dispatchId: activeDispatch.dispatchId,
      machineId: selectedMachineId,
      recipeId: assignableRecipes[0].recipeId,
      scheduledStart,
      scheduledEnd,
    });
  }

  const canAssign = Boolean(selectedMachineId && assignableRecipes[0]);
  const canApplySuggested = Boolean(
    activeDispatch?.scheduledStart && activeDispatch?.scheduledEnd,
  );

  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: 22,
        }}
      >
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800 }}>派工排程</h1>
          <p
            style={{
              fontSize: 12,
              color: "var(--text3)",
              marginTop: 4,
              fontFamily: "monospace",
            }}
          >
            ROLE C · POSTGRESQL · {statusLine(dispatchesQuery)}
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <select
            value={strategy}
            onChange={(e) => setStrategy(e.target.value as Strategy)}
            style={selectStyle}
          >
            {STRATEGIES.map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
          <button
            onClick={() => suggest.mutate()}
            disabled={suggest.isPending}
            style={buttonStyle}
          >
            {suggest.isPending ? "產生中…" : "產生建議"}
          </button>
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4,1fr)",
          gap: 14,
          marginBottom: 20,
        }}
      >
        <KpiCard
          label="待派工 WIP"
          value={summary.pending}
          sub="由使用者建立"
          color="var(--yellow)"
          icon="🗂️"
        />
        <KpiCard
          label="排程中"
          value={summary.scheduling}
          sub={`策略 ${strategy}`}
          color="var(--purple)"
          icon="📌"
        />
        <KpiCard
          label="待上機"
          value={summary.ready}
          sub="已完成派工"
          color="var(--green)"
          icon="✅"
        />
        <KpiCard
          label="不可用機台"
          value={summary.blockedMachines}
          sub="派工時自動排除"
          color="var(--red)"
          icon="⚠️"
        />
      </div>

      <StrategyBar strategy={strategy} onReplan={handleReplan} />

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "320px 1fr 340px",
          gap: 16,
        }}
      >
        <DispatchForm
          experimentItems={experimentItems}
          submitting={create.isPending}
          onSubmit={(payload) => create.mutate(payload)}
        />
        <DispatchTable
          dispatches={dispatches}
          activeDispatchId={activeDispatch?.dispatchId ?? ""}
          onSelect={setActiveDispatchId}
        />
        <DispatchAssignPanel
          activeDispatch={activeDispatch}
          assignableMachines={assignableMachines}
          assignableRecipes={assignableRecipes}
          scheduledStart={scheduledStart}
          scheduledEnd={scheduledEnd}
          canApplySuggested={canApplySuggested}
          canAssign={canAssign}
          assigning={assign.isPending}
          onScheduleChange={updateScheduleDraft}
          onApplySuggested={applySuggestedSchedule}
          onAssign={handleAssign}
        />
      </div>
    </div>
  );
}

function statusLine(query: { isLoading: boolean; isError: boolean }): string {
  if (query.isLoading) return "讀取資料庫中";
  if (query.isError) return "後端或 PostgreSQL 尚未啟動";
  return "已連線 PostgreSQL";
}

const selectStyle: React.CSSProperties = {
  background: "var(--s2)",
  border: "1px solid var(--border)",
  color: "var(--text)",
  padding: "9px 10px",
  borderRadius: 8,
  fontSize: 12,
};

const buttonStyle: React.CSSProperties = {
  background: "var(--blue)",
  border: "1px solid var(--border)",
  color: "#fff",
  padding: "9px 12px",
  borderRadius: 8,
  fontSize: 12,
  cursor: "pointer",
};

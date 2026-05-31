"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
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

// B 的 wips.priority（英文）→ 派工單優先級（中文）。
const PRIORITY_MAP: Record<string, string> = {
  normal: "一般",
  high: "高",
  urgent: "特急",
};

// /api/wips 回傳的 WIP（snake_case），這裡只取派工挑單需要的欄位。
type WipLite = {
  id: string;
  wip_no: string;
  order_no: string;
  experiment_item: string | null;
  priority: string;
  status: string;
  lab_name: string | null;
};

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
    // 機台狀態(閒置/使用中/保養/故障)會被其他流程改動；定時刷新才能即時抓到可派工機台。
    refetchInterval: 10000,
  });
  const recipesQuery = useQuery({
    queryKey: ["recipes"],
    queryFn: recipesApi.list,
  });
  const dispatchesQuery = useQuery({
    queryKey: ["dispatches"],
    queryFn: dispatchesApi.list,
  });
  const wipsQuery = useQuery({
    queryKey: ["wips", "for-dispatch"],
    // B 的 /api/wips 回傳裸陣列（或 { data: [...] }），不是 { items }。
    queryFn: () =>
      apiGet<WipLite[] | { data?: WipLite[] }>(
        "/api/wips?status=waiting_schedule&own_lab_only=true"
      ),
  });

  const [prefill, setPrefill] = useState<Record<string, string> | null>(null);
  const [prefillNonce, setPrefillNonce] = useState(0);

  const machines = useMemo(() => machinesQuery.data ?? [], [machinesQuery.data]);
  const recipes = useMemo(() => recipesQuery.data ?? [], [recipesQuery.data]);
  const dispatches = useMemo(() => dispatchesQuery.data ?? [], [dispatchesQuery.data]);

  const invalidateDispatches = () => {
    queryClient.invalidateQueries({ queryKey: ["dispatches"] });
    // WIP 狀態會隨建立/排程/指派前進（C→B 連動），一併刷新待排程挑單清單。
    queryClient.invalidateQueries({ queryKey: ["wips", "for-dispatch"] });
  };

  // 待排程 WIP（B 已送排程、尚未建立派工單者）→ 供挑單快速填入。
  const waitingWips = useMemo(() => {
    const raw = wipsQuery.data;
    const items: WipLite[] = Array.isArray(raw) ? raw : (raw?.data ?? []);
    const dispatchedWipNos = new Set(
      (dispatchesQuery.data ?? []).map((dispatch) => dispatch.wipId)
    );
    return items.filter(
      (wip) => wip.status === "waiting_schedule" && !dispatchedWipNos.has(wip.wip_no)
    );
  }, [wipsQuery.data, dispatchesQuery.data]);

  function pickWipForDispatch(wip: WipLite) {
    setPrefill({
      dispatchId: `DSP-${wip.wip_no}`,
      wipId: wip.wip_no,
      orderId: wip.order_no,
      experimentItem: wip.experiment_item ?? "",
      priority: PRIORITY_MAP[wip.priority] ?? "一般",
      dueAt: "",
    });
    setPrefillNonce((nonce) => nonce + 1);
  }

  const create = useMutation({
    mutationFn: (payload: CreateDispatchPayload) => dispatchesApi.create(payload),
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
    () => Array.from(new Set(machines.flatMap((machine) => machine.supportedItems))),
    [machines]
  );

  const activeDispatch =
    dispatches.find((dispatch) => dispatch.dispatchId === activeDispatchId) ??
    // 預設挑第一筆「待派工」且有實驗項目的派工單(面板就是對它操作),
    // 而非清單第一列(常是尚未產生、無實驗項目的空列 → 會顯示「無可用機台」)。
    dispatches.find((d) => d.status === "待派工" && d.experimentItem) ??
    dispatches.find((d) => d.experimentItem) ??
    dispatches[0];
  const activeScheduleDraft = activeDispatch
    ? scheduleDrafts[activeDispatch.dispatchId]
    : undefined;
  const scheduledStart =
    activeScheduleDraft?.scheduledStart ?? toDateTimeLocal(activeDispatch?.scheduledStart);
  const scheduledEnd =
    activeScheduleDraft?.scheduledEnd ?? toDateTimeLocal(activeDispatch?.scheduledEnd);

  function updateScheduleDraft(field: "scheduledStart" | "scheduledEnd", value: string) {
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
        !BLOCKED.includes(machine.status)
    );
  }, [activeDispatch, machines]);

  const selectedMachineId =
    activeDispatch?.suggestedMachineId &&
    assignableMachines.some((machine) => machine.machineId === activeDispatch.suggestedMachineId)
      ? activeDispatch.suggestedMachineId
      : assignableMachines[0]?.machineId;

  const assignableRecipes = useMemo(() => {
    if (!activeDispatch || !selectedMachineId) return [];
    return recipes.filter(
      (recipe) =>
        recipe.experimentItem === activeDispatch.experimentItem &&
        recipe.machineIds.includes(selectedMachineId)
    );
  }, [activeDispatch, recipes, selectedMachineId]);

  // 當沒有可派工機台時，說明「為何」：是沒有支援該實驗項目的機台(能力問題)，
  // 還是支援的機台目前都不可用(狀態問題)。避免誤以為把機台轉閒置就能派。
  const machineHint = useMemo(() => {
    const item = activeDispatch?.experimentItem;
    if (!item) return "未選擇 WIP";
    if (assignableMachines.length > 0) return null;
    const supporting = machines.filter((m) => m.supportedItems.includes(item));
    return supporting.length === 0
      ? `尚無支援「${item}」的機台 — 請至「機台管理」新增或編輯機台支援此項目`
      : "支援的機台目前皆不可用(保養 / 故障 / 停用)";
  }, [activeDispatch, assignableMachines, machines]);

  const summary = useMemo(
    () => ({
      pending: dispatches.filter((dispatch) => dispatch.status === "待排程").length,
      scheduling: dispatches.filter((dispatch) => dispatch.status === "待派工").length,
      ready: dispatches.filter((dispatch) => dispatch.status === "待上機").length,
      blockedMachines: machines.filter((machine) => BLOCKED.includes(machine.status)).length,
    }),
    [dispatches, machines]
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

  // 只有「待派工」的派工單能確認派工（待上機已派完，待排程需先排程）。
  const canAssign = Boolean(
    selectedMachineId && assignableRecipes[0] && activeDispatch?.status === "待派工"
  );
  const canApplySuggested = Boolean(activeDispatch?.scheduledStart && activeDispatch?.scheduledEnd);

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
          <button onClick={() => suggest.mutate()} disabled={suggest.isPending} style={buttonStyle}>
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
          label="待排程 WIP"
          value={summary.pending}
          sub="由使用者建立"
          color="var(--yellow)"
          icon="🗂️"
        />
        <KpiCard
          label="待派工"
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

      <div style={waitingWipsBoxStyle}>
        <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 8 }}>
          待排程 WIP{" "}
          <span style={{ color: "var(--text3)", fontWeight: 400 }}>
            （從「分貨 / WIP」頁送排程後出現；點選即可快速填入左側表單）
          </span>
        </div>
        {wipsQuery.isLoading ? (
          <div style={hintTextStyle}>讀取中…</div>
        ) : waitingWips.length === 0 ? (
          <div style={hintTextStyle}>
            目前沒有待排程的 WIP。請先到「分貨 / WIP」頁建立 WIP
          </div>
        ) : (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {waitingWips.map((wip) => (
              <button key={wip.id} onClick={() => pickWipForDispatch(wip)} style={wipChipStyle}>
                {wip.wip_no} · {wip.experiment_item ?? "-"} · {wip.lab_name ?? "-"}
              </button>
            ))}
          </div>
        )}
      </div>

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
          prefill={prefill}
          prefillNonce={prefillNonce}
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
          machineHint={machineHint}
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

const waitingWipsBoxStyle: React.CSSProperties = {
  background: "var(--s1)",
  border: "1px solid var(--border)",
  borderRadius: 10,
  padding: 14,
  marginBottom: 16,
};

const hintTextStyle: React.CSSProperties = {
  fontSize: 12,
  color: "var(--text3)",
};

const wipChipStyle: React.CSSProperties = {
  background: "var(--s2)",
  border: "1px solid var(--border)",
  color: "var(--text)",
  padding: "7px 10px",
  borderRadius: 8,
  fontSize: 12,
  cursor: "pointer",
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

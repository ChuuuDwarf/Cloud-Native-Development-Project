"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { RoleLabel, type RoleName } from "@/constants/status-labels";
import { useAuth } from "@/contexts/AuthContext";
import { apiGet, apiPost } from "@/lib/api";
import { getErrorMessage } from "@/lib/error";
import { masterDataApi } from "@/services/master-data-api";
import type {
  CurrentUser,
  Sample,
  SampleAction,
  SampleFilter,
  SampleHistory,
  Transfer,
  Wip,
  WipExecutionDetail,
} from "./types";
import { SampleDetailModal } from "./components/SampleDetailModal";
import { SampleTable } from "./components/SampleTable";
import { SummaryCard } from "./components/SummaryCard";
import {
  getFilterButtonStyle,
  countBadgeStyle,
  currentUserBoxStyle,
  currentUserIdentityPartStyle,
  currentUserIdentityStyle,
  errorStyle,
  filterBarStyle,
  headerActionsStyle,
  headerStyle,
  panelHeaderStyle,
  panelHintStyle,
  panelStyle,
  secondaryButtonStyle,
  subtitleStyle,
  successStyle,
  summaryGridStyle,
  titleStyle,
} from "./styles";
import {
  filterSamplesByView,
  getDisplaySampleStatus,
  getUserLab,
  isActiveSampleStatus,
  isFactoryUser as checkIsFactoryUser,
  isLabUser as checkIsLabUser,
  isSampleInCurrentLab,
  isSampleVisibleForUser,
  normalizeSampleFilter,
} from "./utils/sampleDisplay";
import {
  findCompletedTransferBoundaryIndex,
  parseExperimentsFromSummary,
} from "../transfer/utils/transferFlow";

type ApiListResponse<T> = T[] | { data?: T[] };
type ApiDataResponse<T> = { data?: T };

function normalizeApiArray<T>(payload: ApiListResponse<T>): T[] {
  if (Array.isArray(payload)) return payload;
  return Array.isArray(payload.data) ? payload.data : [];
}

export default function SamplePage() {
  const { user: authUser } = useAuth();
  const masterQuery = useQuery({
    queryKey: ["master-data"],
    queryFn: masterDataApi.fetch,
  });
  const [samples, setSamples] = useState<Sample[]>([]);
  const [wips, setWips] = useState<Wip[]>([]);
  const [transfers, setTransfers] = useState<Transfer[]>([]);
  const [sampleHistories, setSampleHistories] = useState<SampleHistory[]>([]);
  const [wipExecutionDetails, setWipExecutionDetails] = useState<
    Record<string, WipExecutionDetail>
  >({});
  const [wipExecutionLoading, setWipExecutionLoading] = useState(false);
  const [selectedSampleId, setSelectedSampleId] = useState<string | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyVisibleCount, setHistoryVisibleCount] = useState(5);
  const [submitting, setSubmitting] = useState(false);
  const [sampleFilter, setSampleFilter] = useState<SampleFilter>("current");
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const currentLab = masterQuery.data?.labs.find((lab) => lab.id === authUser?.labId);
  const currentDepartment = masterQuery.data?.departments.find(
    (department) => department.id === authUser?.departmentId
  );

  const currentUser = useMemo<CurrentUser | null>(() => {
    if (!authUser) return null;

    return {
      id: authUser.id,
      name: authUser.name,
      role: authUser.role,
      department: currentDepartment?.name ?? currentDepartment?.code ?? authUser.departmentId ?? "",
      lab_name: currentLab?.name ?? currentLab?.code ?? null,
      email: authUser.email,
    };
  }, [authUser, currentDepartment, currentLab]);

  const roleLabel = currentUser
    ? (RoleLabel[currentUser.role as RoleName] ?? currentUser.role)
    : "—";
  const identityLabName = currentUser && checkIsLabUser(currentUser) ? currentLab?.name : undefined;
  const currentUserIdentityParts = currentUser
    ? [identityLabName, roleLabel, currentUser.name].filter((part): part is string => Boolean(part))
    : ["尚未取得登入身分"];

  const isFactoryUser = currentUser ? checkIsFactoryUser(currentUser) : false;
  const isLabUser = currentUser ? checkIsLabUser(currentUser) : false;
  const operatorName = currentUser?.name ?? "";

  const outgoingTransfersBySampleId = useMemo(() => {
    const map = new Map<string, Transfer>();
    if (!currentUser) return map;

    const currentLab = getUserLab(currentUser);
    const isLabUser = checkIsLabUser(currentUser);

    function getTransferPriority(transfer: Transfer) {
      if (!isLabUser || !currentLab) return 0;

      const isIncomingToCurrentLab = transfer.to_lab === currentLab;
      const isOutgoingFromCurrentLab = transfer.from_lab === currentLab;

      // 樣品目前在自己 Lab，代表要看「別人交給我」的待收樣資訊。
      // 樣品不在自己 Lab，代表要看「我交出去」的交接結果。
      const relatedSample = samples.find((sample) => sample.id === transfer.target_id);
      const location = relatedSample?.current_location ?? "";
      const sampleInCurrentLab = Boolean(location.startsWith(currentLab));

      if (sampleInCurrentLab && isIncomingToCurrentLab) return 3;
      if (!sampleInCurrentLab && isOutgoingFromCurrentLab) return 3;
      if (isOutgoingFromCurrentLab || isIncomingToCurrentLab) return 2;

      return 1;
    }

    transfers
      .filter((transfer) => transfer.target_type === "sample")
      .filter((transfer) => {
        if (!isLabUser || !currentLab) return true;
        return transfer.from_lab === currentLab || transfer.to_lab === currentLab;
      })
      .forEach((transfer) => {
        const existing = map.get(transfer.target_id);

        if (!existing) {
          map.set(transfer.target_id, transfer);
          return;
        }

        const existingPriority = getTransferPriority(existing);
        const nextPriority = getTransferPriority(transfer);

        if (nextPriority > existingPriority) {
          map.set(transfer.target_id, transfer);
          return;
        }

        if (nextPriority < existingPriority) {
          return;
        }

        const existingTime = new Date(existing.updated_at ?? existing.created_at).getTime();
        const nextTime = new Date(transfer.updated_at ?? transfer.created_at).getTime();

        if (nextTime > existingTime) {
          map.set(transfer.target_id, transfer);
        }
      });

    return map;
  }, [transfers, samples, currentUser]);

  const filterOptions = useMemo(() => {
    if (isFactoryUser) {
      return [
        { value: "all", label: "全部" },
        { value: "active", label: "進行中" },
        { value: "outbound", label: "待取件" },
        { value: "picked_up", label: "已取件" },
      ] as Array<{ value: SampleFilter; label: string }>;
    }

    return [
      { value: "current", label: "目前在本 Lab" },
      { value: "outbound", label: "待取件" },
      { value: "picked_up", label: "已取件紀錄" },
      { value: "all", label: "全部紀錄" },
    ] as Array<{ value: SampleFilter; label: string }>;
  }, [isFactoryUser]);

  const visibleSamples = useMemo(() => {
    if (!currentUser) return [];

    const nextSamples = filterSamplesByView(samples, currentUser, sampleFilter);

    if (isLabUser && sampleFilter === "picked_up") {
      return nextSamples.filter((sample) => {
        const transfer = outgoingTransfersBySampleId.get(sample.id);
        return getDisplaySampleStatus(sample, currentUser, transfer) === "picked_up";
      });
    }

    return nextSamples;
  }, [samples, currentUser, sampleFilter, isLabUser, outgoingTransfersBySampleId]);

  const selectedSample = useMemo(() => {
    return visibleSamples.find((sample) => sample.id === selectedSampleId) ?? null;
  }, [visibleSamples, selectedSampleId]);

  const selectedSampleInCurrentLab = useMemo(() => {
    if (!currentUser) return false;

    return isSampleInCurrentLab(selectedSample, currentUser);
  }, [selectedSample, currentUser]);

  const selectedSampleOutgoingTransfer = useMemo(() => {
    if (!selectedSample) return undefined;
    return outgoingTransfersBySampleId.get(selectedSample.id);
  }, [selectedSample, outgoingTransfersBySampleId]);

  const selectedWips = useMemo(() => {
    if (!selectedSample) return [];
    return wips.filter((wip) => wip.sample_id === selectedSample.id);
  }, [wips, selectedSample]);

  const visibleSelectedWips = useMemo(() => {
    if (!selectedSample || !currentUser) return [];

    if (
      currentUser.role === "system_admin" ||
      checkIsFactoryUser(currentUser) ||
      checkIsLabUser(currentUser)
    ) {
      return selectedWips;
    }

    return [];
  }, [selectedWips, selectedSample, currentUser]);

  const wipsByLab = useMemo(() => {
    return visibleSelectedWips.reduce<Record<string, Wip[]>>((groups, wip) => {
      const labName = wip.lab_name ?? "未指定實驗室";

      if (!groups[labName]) {
        groups[labName] = [];
      }

      groups[labName].push(wip);
      return groups;
    }, {});
  }, [visibleSelectedWips]);

  const currentLabWips = useMemo(() => {
    if (!currentUser) return [];

    const currentLab = getUserLab(currentUser);

    if (!currentLab) return [];

    return selectedWips.filter((wip) => wip.lab_name === currentLab);
  }, [selectedWips, currentUser]);

  const sampleFlowState = useMemo(() => {
    if (!selectedSample || !currentUser) {
      return {
        currentLabFlowReady: false,
        hasNextExperiment: false,
        nextLabDiffers: false,
        nextLabSame: false,
      };
    }

    const currentLab = getUserLab(currentUser);
    const requestedExperiments = parseExperimentsFromSummary(selectedSample.experiment_item);
    const completedBoundary = findCompletedTransferBoundaryIndex(
      requestedExperiments,
      selectedWips,
      currentLab
    );
    const nextExperiment = requestedExperiments[completedBoundary + 1] ?? null;

    return {
      currentLabFlowReady: completedBoundary >= 0,
      hasNextExperiment: Boolean(nextExperiment),
      nextLabDiffers: Boolean(nextExperiment && nextExperiment.lab_name !== currentLab),
      nextLabSame: Boolean(nextExperiment && nextExperiment.lab_name === currentLab),
    };
  }, [selectedSample, selectedWips, currentUser]);

  const canNotifyPickup =
    Boolean(selectedSample) &&
    !isFactoryUser &&
    selectedSampleInCurrentLab &&
    (selectedSample?.status === "split" || selectedSample?.status === "pending_transfer") &&
    sampleFlowState.currentLabFlowReady &&
    !sampleFlowState.hasNextExperiment;

  const shouldShowTransferAction =
    Boolean(selectedSample) &&
    !isFactoryUser &&
    selectedSampleInCurrentLab &&
    (selectedSample?.status === "split" || selectedSample?.status === "pending_transfer") &&
    sampleFlowState.currentLabFlowReady &&
    sampleFlowState.nextLabDiffers;

  const baseSamplesForCount = useMemo(() => {
    if (!currentUser) return [];

    return samples.filter((sample) => isSampleVisibleForUser(sample, currentUser));
  }, [samples, currentUser]);

  const pendingReceiveCount = baseSamplesForCount.filter((sample) => {
    if (sample.status !== "pending_receive") return false;

    if (isLabUser && currentUser) {
      return isSampleInCurrentLab(sample, currentUser);
    }

    return true;
  }).length;

  const inLabCount = baseSamplesForCount.filter((sample) => {
    if (
      !["received", "split", "pending_transfer", "transferring", "in_storage", "outbound"].includes(
        sample.status
      )
    ) {
      return false;
    }

    if (isLabUser && currentUser) {
      return isSampleInCurrentLab(sample, currentUser);
    }

    return true;
  }).length;

  const outboundCount = baseSamplesForCount.filter((sample) => {
    if (sample.status !== "outbound") return false;

    if (isLabUser && currentUser) {
      return isSampleInCurrentLab(sample, currentUser);
    }

    return true;
  }).length;

  const pickedUpCount = baseSamplesForCount.filter((sample) => {
    if (sample.status !== "picked_up") return false;

    if (isLabUser && currentUser) {
      const transfer = outgoingTransfersBySampleId.get(sample.id);
      return getDisplaySampleStatus(sample, currentUser, transfer) === "picked_up";
    }

    return true;
  }).length;
  const activeCount = baseSamplesForCount.filter((sample) =>
    isActiveSampleStatus(sample.status)
  ).length;
  const totalCount = baseSamplesForCount.length;

  const summaryCards = isFactoryUser
    ? [
        { label: "我的進行中", value: activeCount },
        { label: "我的待取件", value: outboundCount },
        { label: "我的已取件", value: pickedUpCount },
        { label: "我的全部樣品", value: totalCount },
      ]
    : [
        { label: "待收樣", value: pendingReceiveCount },
        { label: "實驗室內", value: inLabCount },
        { label: "待取件", value: outboundCount },
        { label: "已取件", value: pickedUpCount },
      ];

  const visibleHistories = sampleHistories.slice(0, historyVisibleCount);
  const canFactoryConfirmPickup =
    Boolean(selectedSample) &&
    isFactoryUser &&
    selectedSample?.status === "outbound" &&
    selectedSample?.applicant_name === currentUser?.name;

  const shouldShowFactoryAction = canFactoryConfirmPickup;
  const shouldShowLabActions =
    Boolean(selectedSample) &&
    !isFactoryUser &&
    selectedSampleInCurrentLab &&
    (selectedSample?.status === "pending_receive" ||
      selectedSample?.status === "received" ||
      selectedSample?.status === "pending_transfer" ||
      selectedSample?.status === "transferring" ||
      selectedSample?.status === "split");

  const shouldShowActionSection = shouldShowFactoryAction || shouldShowLabActions;

  async function loadData() {
    if (!currentUser) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError("");
      setSuccessMessage("");

      const nextSampleFilter = normalizeSampleFilter(currentUser, sampleFilter);
      setSampleFilter(nextSampleFilter);

      const [samplePayload, wipPayload, transferPayload] = await Promise.all([
        apiGet<ApiListResponse<Sample>>("/api/samples?scope=all"),
        apiGet<ApiListResponse<Wip>>("/api/wips"),
        apiGet<ApiListResponse<Transfer>>("/api/transfers"),
      ]);

      const sampleData = normalizeApiArray(samplePayload);
      const wipData = normalizeApiArray(wipPayload);
      const transferData = normalizeApiArray(transferPayload);
      const filteredSamples = filterSamplesByView(sampleData, currentUser, nextSampleFilter);

      setSamples(sampleData);
      setWips(wipData);
      setTransfers(transferData);

      if (selectedSampleId) {
        const stillVisible = filteredSamples.some((item) => item.id === selectedSampleId);

        if (!stillVisible) {
          setSelectedSampleId(null);
          setSampleHistories([]);
          setDetailOpen(false);
        }
      }
    } catch (err) {
      setError(getErrorMessage(err, "載入資料失敗"));
    } finally {
      setLoading(false);
    }
  }

  async function loadSampleHistory(sampleId: string) {
    try {
      setHistoryLoading(true);
      const data = await apiGet<SampleHistory[]>(`/api/samples/${sampleId}/history`);
      setSampleHistories(data);
    } catch (err) {
      setError(getErrorMessage(err, "載入樣品歷程失敗"));
    } finally {
      setHistoryLoading(false);
    }
  }

  async function loadWipExecutionDetails(sampleId: string) {
    const targetWips = wips.filter((wip) => wip.sample_id === sampleId);

    if (targetWips.length === 0) {
      setWipExecutionDetails({});
      return;
    }

    try {
      setWipExecutionLoading(true);

      const results = await Promise.allSettled(
        targetWips.map(async (wip) => {
          const payload = await apiGet<ApiDataResponse<WipExecutionDetail>>(
            `/api/experiment-runs/${wip.wip_no}`
          );

          return [wip.wip_no, payload.data] as const;
        })
      );

      const nextDetails: Record<string, WipExecutionDetail> = {};

      results.forEach((result) => {
        if (result.status !== "fulfilled") return;

        const [wipNo, detail] = result.value;
        if (detail) {
          nextDetails[wipNo] = detail;
        }
      });

      setWipExecutionDetails(nextDetails);
    } catch (err) {
      setError(getErrorMessage(err, "載入 WIP 機台履歷失敗"));
    } finally {
      setWipExecutionLoading(false);
    }
  }

  async function openDetail(sampleId: string) {
    setSelectedSampleId(sampleId);
    setDetailOpen(true);
    setSampleHistories([]);
    setWipExecutionDetails({});
    setHistoryVisibleCount(5);
    setError("");
    setSuccessMessage("");

    await Promise.all([loadSampleHistory(sampleId), loadWipExecutionDetails(sampleId)]);
  }

  function closeDetail() {
    setDetailOpen(false);
    setWipExecutionDetails({});
  }

  async function runSampleAction(sampleId: string, action: SampleAction) {
    if (!currentUser) {
      setError("尚未取得登入身分，請重新整理後再試");
      return;
    }

    const targetSample = samples.find((sample) => sample.id === sampleId) ?? null;

    const isFactoryPickup =
      isFactoryUser &&
      action === "pickup_confirmed" &&
      targetSample?.status === "outbound" &&
      targetSample.applicant_name === currentUser.name;

    const isLabOperationAllowed = !isFactoryUser && isSampleInCurrentLab(targetSample, currentUser);

    if (!isLabOperationAllowed && !isFactoryPickup) {
      setError("只能操作目前位於自己 Lab 內的樣品；歷史紀錄只能查看，不能處理");
      return;
    }

    if (isFactoryUser && action !== "pickup_confirmed") {
      setError("廠區使用者不能執行收樣、分貨或通知取件");
      return;
    }

    try {
      setSubmitting(true);
      setError("");
      setSuccessMessage("");

      const body: Record<string, string | boolean> = {
        action,
        operator_name: operatorName,
      };

      if (action === "outbound") {
        body.note = "所有實驗已完成，已通知原使用者取件";
        body.confirm_notify_pickup = true;
      }

      if (action === "pickup_confirmed") {
        body.current_location = "已由使用者取回";
      }

      await apiPost(`/api/samples/${sampleId}/actions`, body);

      if (action === "receive") {
        setSuccessMessage("已完成收樣，樣品仍會保留在目前實驗室的收樣管理清單中");
      }

      if (action === "outbound") {
        setSuccessMessage("已通知取件，樣品已移至目前實驗室的待取件區");
      }

      if (action === "pickup_confirmed") {
        setSuccessMessage("已確認廠區取件");
      }

      await loadData();
      await loadSampleHistory(sampleId);
    } catch (err) {
      setError(getErrorMessage(err, "操作失敗"));
    } finally {
      setSubmitting(false);
    }
  }

  function getNextStep(sample: Sample | null) {
    if (!sample) return "請先選擇樣品";
    if (!currentUser) return "尚未取得登入身分";

    if (isFactoryUser) {
      if (sample.status === "pending_receive") return "樣品已送出，等待實驗室確認收樣。";
      if (sample.status === "received") return "實驗室已收樣，等待建立或執行實驗子單。";
      if (sample.status === "split") return "樣品已進入實驗流程，可在此追蹤 WIP / 實驗子單進度。";
      if (sample.status === "pending_transfer") return "本階段實驗已完成，可交接至下一站。";
      if (sample.status === "outbound")
        return "實驗已完成，樣品等待取回。實際拿到樣品後，可以確認取件。";
      if (sample.status === "picked_up") return "樣品已取回，流程完成。";
      return "目前僅提供樣品狀態與歷程查詢。";
    }

    if (!isSampleInCurrentLab(sample, currentUser)) {
      const transfer = outgoingTransfersBySampleId.get(sample.id);

      if (transfer?.status === "received") {
        return "此樣品已被接收實驗室收樣。你只能查看本實驗室的交接紀錄，不能查看接收實驗室後續處理狀態，也不能執行操作。";
      }

      if (transfer?.status === "transferring") return "此樣品已送出，等待接收實驗室確認收樣。";
      if (transfer?.status === "pending") return "此樣品已有交接單，尚未送出。";
      return "此樣品已離開你的實驗室。本畫面只保留你所屬 Lab 的歷程紀錄與交接確認結果，不能查看對方 Lab 的後續狀態，也不能執行操作。";
    }

    if (sample.status === "pending_receive") return "樣品尚未完成收樣，下一步是確認收樣。";
    if (sample.status === "received")
      return "樣品已完成收樣，下一步請前往 WIP / 分貨管理建立實驗子單。";
    if (sample.status === "split" && currentLabWips.length === 0) {
      return "樣品已建立 WIP，但目前登入 Lab 沒有可處理的 WIP。";
    }

    if (
      sample.status === "split" &&
      currentLabWips.length > 0 &&
      !sampleFlowState.currentLabFlowReady
    ) {
      return "此樣品仍有本 Lab 的 WIP 尚未完成，完成後才能進入下一步。";
    }

    if (sample.status === "split" && sampleFlowState.nextLabSame) {
      return "此樣品下一個實驗仍在本 Lab，請繼續完成本 Lab 的 WIP。";
    }

    if (sample.status === "split" && sampleFlowState.nextLabDiffers) {
      return "本 Lab 的 WIP 已完成，但此樣品後面還有其他實驗室要處理。下一步請前往交接流轉，移交給下一個 Lab。";
    }

    if (sample.status === "pending_transfer") {
      return "本 Lab 目前已建立的 WIP 都完成，樣品可前往交接流轉；若尚未送出，也可以回到 WIP / 分貨管理繼續補分貨。";
    }

    if (
      sample.status === "split" &&
      sampleFlowState.currentLabFlowReady &&
      !sampleFlowState.hasNextExperiment
    ) {
      return "此樣品已完成最後一個 Lab 的實驗，可通知原使用者取件，並將樣品移至待取件區。";
    }
    if (sample.status === "transferring") return "樣品正在跨實驗室交接中，等待下一個實驗室簽收。";
    if (sample.status === "outbound") return "已通知原使用者取件，樣品目前在待取件區。";
    if (sample.status === "picked_up")
      return "樣品已由原使用者取回，流程完成。此筆會保留在已取件紀錄。";
    if (sample.status === "in_storage")
      return "樣品目前已入庫保存。若不做倉儲流程，後續可改為直接通知取件。";

    return "請依樣品狀態判斷下一步。";
  }

  function goToWipPage(sampleId: string) {
    window.location.href = `/wip?sampleId=${sampleId}`;
  }

  function goToTransferPage() {
    window.location.href = "/transfer";
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentUser?.id, currentUser?.role, currentUser?.lab_name]);

  useEffect(() => {
    if (!currentUser) return;

    const nextFilter = normalizeSampleFilter(currentUser, sampleFilter);

    if (nextFilter !== sampleFilter) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setSampleFilter(nextFilter);
      setSelectedSampleId(null);
      setDetailOpen(false);
      setSampleHistories([]);
      setHistoryVisibleCount(5);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentUser?.role]);

  if (!currentUser) {
    return <div style={panelHintStyle}>尚未取得登入身分</div>;
  }

  return (
    <div>
      <div style={headerStyle}>
        <div>
          <h1 style={titleStyle}>{isFactoryUser ? "我的樣品追蹤" : "收樣與樣品追蹤"}</h1>
          <p style={subtitleStyle}>
            {isFactoryUser
              ? "SAMPLE TRACKING · 廠區使用者可查看自己已送樣後的樣品狀態、待取件與已取件紀錄"
              : "SAMPLE TRACKING · 預設顯示目前仍在本 Lab 的樣品，也可切換查看待取件與歷史紀錄"}
          </p>
        </div>

        <div style={headerActionsStyle}>
          {!isFactoryUser && (
            <button onClick={goToTransferPage} style={secondaryButtonStyle}>
              交接流轉
            </button>
          )}
          <button onClick={loadData} style={secondaryButtonStyle}>
            重新整理
          </button>
        </div>
      </div>

      <section style={summaryGridStyle}>
        {summaryCards.map((card) => (
          <SummaryCard key={card.label} label={card.label} value={card.value} />
        ))}
      </section>

      <section style={currentUserBoxStyle}>
        <div style={{ fontWeight: 800 }}>目前操作身分</div>
        <div style={currentUserIdentityStyle}>
          {currentUserIdentityParts.map((part) => (
            <span key={part} style={currentUserIdentityPartStyle}>
              {part}
            </span>
          ))}
        </div>
      </section>

      {error && <div style={errorStyle}>{error}</div>}
      {successMessage && <div style={successStyle}>{successMessage}</div>}

      <section style={panelStyle}>
        <div style={panelHeaderStyle}>
          <div>
            <div style={{ fontWeight: 800 }}>{isFactoryUser ? "我的樣品清單" : "樣品清單"}</div>
            <div style={panelHintStyle}>
              {isFactoryUser
                ? "可切換進行中、待取件、已取件與全部紀錄。"
                : "預設看目前仍在本 Lab 的樣品；轉交後只顯示交接狀態，不顯示接收實驗室後續細節。"}
            </div>
          </div>

          <span style={countBadgeStyle}>{visibleSamples.length} 筆</span>
        </div>

        <div style={filterBarStyle}>
          {filterOptions.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => {
                setSampleFilter(option.value);
                setSelectedSampleId(null);
                setDetailOpen(false);
                setSampleHistories([]);
              }}
              style={getFilterButtonStyle(sampleFilter === option.value)}
            >
              {option.label}
            </button>
          ))}
        </div>

        <SampleTable
          loading={loading}
          samples={visibleSamples}
          selectedSampleId={selectedSampleId}
          detailOpen={detailOpen}
          currentUser={currentUser}
          outgoingTransfersBySampleId={outgoingTransfersBySampleId}
          onOpenDetail={openDetail}
        />
      </section>

      {detailOpen && selectedSample && (
        <SampleDetailModal
          sample={selectedSample}
          currentUser={currentUser}
          selectedSampleOutgoingTransfer={selectedSampleOutgoingTransfer}
          visibleSelectedWips={visibleSelectedWips}
          wipsByLab={wipsByLab}
          wipExecutionDetails={wipExecutionDetails}
          wipExecutionLoading={wipExecutionLoading}
          sampleHistories={sampleHistories}
          visibleHistories={visibleHistories}
          historyLoading={historyLoading}
          historyVisibleCount={historyVisibleCount}
          submitting={submitting}
          canFactoryConfirmPickup={canFactoryConfirmPickup}
          selectedSampleInCurrentLab={selectedSampleInCurrentLab}
          allWipsCompleted={canNotifyPickup}
          shouldShowTransferAction={shouldShowTransferAction}
          shouldShowActionSection={shouldShowActionSection}
          isFactoryUser={isFactoryUser}
          nextStepText={getNextStep(selectedSample)}
          onClose={closeDetail}
          onShowMoreHistory={() => setHistoryVisibleCount((count) => count + 5)}
          onCollapseHistory={() => setHistoryVisibleCount(5)}
          onRunSampleAction={runSampleAction}
          onGoToWipPage={goToWipPage}
          onGoToTransferPage={goToTransferPage}
        />
      )}
    </div>
  );
}

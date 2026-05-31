"use client";

import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/contexts/AuthContext";
import { apiGet, apiPost } from "@/lib/api";
import { getErrorMessage, logClientError } from "@/lib/error";
import { masterDataApi } from "@/services/master-data-api";
import type {
  CurrentUser,
  Sample,
  Wip,
  Transfer,
  TransferCandidate,
  SameLabNextCandidate,
  ReturnCandidate,
  Candidate,
} from "./types";
import { sampleStatusText, blockingTransferStatuses } from "./constants";
import {
  normalizeLab,
  getRequestedExperiments,
  findMatchingWipForExperiment,
  isExperimentCompleted,
  getCandidateKey,
} from "./utils/transferFlow";
import {
  TransferModal,
  TransferDetail,
  ReturnDetail,
  SummaryCard,
  InfoLine,
  StatusBadge,
} from "./components/TransferWidgets";
import {
  headerStyle,
  headerActionsStyle,
  titleStyle,
  subtitleStyle,
  currentUserBoxStyle,
  currentUserTitleStyle,
  currentUserTextStyle,
  summaryGridStyle,
  twoColumnGridStyle,
  panelStyle,
  panelHeaderStyle,
  panelTitleStyle,
  hintStyle,
  countBadgeStyle,
  errorStyle,
  successStyle,
  emptyStyle,
  candidateListStyle,
  candidateCardStyle,
  selectedCandidateCardStyle,
  candidateTopRowStyle,
  candidateTitleStyle,
  candidateSubtitleStyle,
  candidateMetaGridStyle,
  readyBadgeStyle,
  warningBadgeStyle,
  secondaryButtonStyle,
  tableStyle,
  thStyle,
  tdStyle,
  monoTdStyle,
  smallActionGroupStyle,
  smallPrimaryButtonStyle,
  smallSecondaryButtonStyle,
  smallDangerButtonStyle,
  statusBadgeStyle,
} from "./styles";

type WipDependencyNextData = {
  orderItemId: number;
  orderNo?: string | null;
  sampleId: string;
  sampleNo: string;
  labId?: string | null;
  labName?: string | null;
  experimentId?: string | null;
  experimentName?: string | null;
  targetGroup?: string | null;
  target?: number | null;
  check?: boolean;
  reason?: string | null;
};

type WipDependencyNextResponse = {
  success: boolean;
  data: WipDependencyNextData | null;
  message?: string | null;
};

type DependencyNextBySampleKey = Record<string, WipDependencyNextData | null>;
type RequestedExperiment = ReturnType<typeof getRequestedExperiments>[number];

export default function SampleTransferPage() {
  const { user: authUser, isLoading: authLoading } = useAuth();

  const masterQuery = useQuery({
    queryKey: ["master-data"],
    queryFn: masterDataApi.fetch,
  });

  const [samples, setSamples] = useState<Sample[]>([]);
  const [wips, setWips] = useState<Wip[]>([]);
  const [transfers, setTransfers] = useState<Transfer[]>([]);

  const [dependencyNextBySampleKey, setDependencyNextBySampleKey] =
    useState<DependencyNextBySampleKey>({});
  const [dependencyNextLoadingBySampleKey, setDependencyNextLoadingBySampleKey] =
    useState<Record<string, boolean>>({});
  const [dependencyNextErrorBySampleKey, setDependencyNextErrorBySampleKey] =
    useState<Record<string, string>>({});

  const [selectedCandidateKey, setSelectedCandidateKey] = useState("");
  const [selectedTransferId, setSelectedTransferId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const currentLabData = masterQuery.data?.labs.find((lab) => lab.id === authUser?.labId);

  const currentDepartment = masterQuery.data?.departments.find(
    (department) => department.id === authUser?.departmentId
  );

  const currentUser = useMemo<CurrentUser | null>(() => {
    if (!authUser) return null;

    const roleLabelMap: Record<string, string> = {
      system_admin: "系統管理者",
      lab_supervisor: "實驗室主管",
      lab_engineer: "實驗室人員",
      plant_user: "廠區使用者",
    };

    return {
      id: authUser.id,
      name: authUser.name,
      role: authUser.role,
      role_name: roleLabelMap[authUser.role] ?? authUser.role,
      department: currentDepartment?.name ?? currentDepartment?.code ?? "",
      lab_name: currentLabData?.name ?? currentLabData?.code ?? null,
      email: authUser.email,
    };
  }, [authUser, currentDepartment, currentLabData]);

  const currentLab = currentUser?.lab_name || currentUser?.department || "";
  const operatorName = currentUser?.name ?? "";

  const isOutgoingTransfer = (transfer: Transfer) =>
    normalizeLab(transfer.from_lab) === normalizeLab(currentLab);

  const isIncomingTransfer = (transfer: Transfer) =>
    normalizeLab(transfer.to_lab) === normalizeLab(currentLab);

  function getSampleDependencyKey(sample: Sample) {
    return `${sample.order_no}:${sample.sample_no}`;
  }

  function getExperimentGroup(experiment: RequestedExperiment) {
    const record = experiment as RequestedExperiment & {
      targetGroup?: string | null;
      target_group?: string | null;
      group?: string | null;
    };

    return record.targetGroup || record.target_group || record.group || "G1";
  }

  function getExperimentTarget(experiment: RequestedExperiment) {
    const record = experiment as RequestedExperiment & {
      target?: number | string | null;
      target_order?: number | string | null;
    };

    const rawTarget = record.target ?? record.target_order ?? 1;
    const target = Number(rawTarget);

    return Number.isFinite(target) ? target : 1;
  }

  function getNextUnlockedExperiments(
    experiments: RequestedExperiment[],
    sampleWips: Wip[]
  ) {
    const groups = new Map<
      string,
      Array<{
        experiment: RequestedExperiment;
        index: number;
      }>
    >();

    experiments.forEach((experiment, index) => {
      const group = getExperimentGroup(experiment);

      if (!groups.has(group)) {
        groups.set(group, []);
      }

      groups.get(group)!.push({ experiment, index });
    });

    return Array.from(groups.values())
      .map((groupExperiments) => {
        const unfinishedExperiments = groupExperiments
          .filter(({ experiment }) => !isExperimentCompleted(sampleWips, experiment))
          .sort((left, right) => {
            const targetDiff =
              getExperimentTarget(left.experiment) - getExperimentTarget(right.experiment);

            if (targetDiff !== 0) return targetDiff;

            return left.index - right.index;
          });

        return unfinishedExperiments[0]?.experiment ?? null;
      })
      .filter((experiment): experiment is RequestedExperiment => experiment !== null);
  }

  function findExistingBlockingTransfer(
    sample: Sample,
    nextWip: Wip | null,
    transfersByTargetIdValue: Record<string, Transfer[]>
  ) {
    const relatedTransfers = [
      ...(transfersByTargetIdValue[sample.id] ?? []),
      ...(nextWip ? (transfersByTargetIdValue[nextWip.id] ?? []) : []),
    ];

    return (
      relatedTransfers.find((transfer) =>
        blockingTransferStatuses.includes(transfer.status)
      ) ?? null
    );
  }

  function getTransferStatusText(transfer: Transfer) {
    if (transfer.status === "pending") {
      return isOutgoingTransfer(transfer) ? "待我方送出" : "等待對方送出";
    }

    if (transfer.status === "transferring") {
      return isIncomingTransfer(transfer) ? "待我方收樣" : "待對方收樣";
    }

    if (transfer.status === "received") {
      return isIncomingTransfer(transfer) ? "我方已收樣" : "對方已收樣";
    }

    if (transfer.status === "cancelled") {
      return "已取消";
    }

    return transfer.status;
  }

  function getTransferActionHint(transfer: Transfer) {
    if (transfer.status === "pending") {
      return isOutgoingTransfer(transfer) ? "尚未送出" : "等待對方送出";
    }

    if (transfer.status === "transferring") {
      return isIncomingTransfer(transfer) ? "等待我方確認收樣" : "已送至對方待收樣區";
    }

    if (transfer.status === "received") {
      return isIncomingTransfer(transfer) ? "我方已收樣" : "對方已收樣";
    }

    if (transfer.status === "cancelled") {
      return "已取消";
    }

    return "";
  }

  const selectedTransfer = useMemo(() => {
    if (!selectedTransferId) return null;

    return transfers.find((transfer) => transfer.id === selectedTransferId) ?? null;
  }, [transfers, selectedTransferId]);

  const wipsBySampleId = useMemo(() => {
    return (Array.isArray(wips) ? wips : []).reduce<Record<string, Wip[]>>((groups, wip) => {
      if (!groups[wip.sample_id]) {
        groups[wip.sample_id] = [];
      }

      groups[wip.sample_id].push(wip);
      return groups;
    }, {});
  }, [wips]);

  const transfersByTargetId = useMemo(() => {
    return transfers.reduce<Record<string, Transfer[]>>((groups, transfer) => {
      if (!groups[transfer.target_id]) {
        groups[transfer.target_id] = [];
      }

      groups[transfer.target_id].push(transfer);
      return groups;
    }, {});
  }, [transfers]);

  function isDependencyNextCompleted(sample: Sample, next: WipDependencyNextData | null) {
    if (!next?.labName || !next.experimentName) return false;

    const sampleWips = wipsBySampleId[sample.id] ?? [];

    return sampleWips.some(
      (wip) =>
        wip.status === "completed" &&
        normalizeLab(wip.lab_name) === normalizeLab(next.labName) &&
        normalizeLab(wip.experiment_item ?? "") === normalizeLab(next.experimentName)
    );
  }

  const displayableTransferSamples = useMemo(() => {
    const result: Sample[] = [];

    samples.forEach((sample) => {
      const sampleWips = wipsBySampleId[sample.id] ?? [];

      if (sample.status === "picked_up") return;
      if (sample.status === "outbound") return;
      if (sample.status === "pending_receive") return;

      const currentLabWips = sampleWips.filter(
        (wip) => normalizeLab(wip.lab_name) === normalizeLab(currentLab)
      );

      if (currentLabWips.length === 0) return;

      const currentLabCompletedWips = currentLabWips.filter(
        (wip) => wip.status === "completed"
      );

      if (currentLabCompletedWips.length === 0) return;

      const currentLabUnfinishedWips = currentLabWips.filter(
        (wip) => wip.status !== "completed"
      );

      if (currentLabUnfinishedWips.length > 0) return;

      const requestedExperiments = getRequestedExperiments(sample);

      if (requestedExperiments.length > 0) {
        result.push(sample);
        return;
      }

      const hasOtherLabUnfinishedWip = sampleWips.some(
        (wip) =>
          wip.status !== "completed" &&
          normalizeLab(wip.lab_name) !== normalizeLab(currentLab)
      );

      if (!hasOtherLabUnfinishedWip) return;

      result.push(sample);
    });

    return result;
  }, [samples, wipsBySampleId, currentLab]);

  const transferCandidates = useMemo<TransferCandidate[]>(() => {
    const result: TransferCandidate[] = [];
    const displayableSampleKeys = new Set(
      displayableTransferSamples.map((sample) => getSampleDependencyKey(sample))
    );

    samples.forEach((sample) => {
      const dependencyKey = getSampleDependencyKey(sample);

      if (!displayableSampleKeys.has(dependencyKey)) return;

      const sampleWips = wipsBySampleId[sample.id] ?? [];
      const requestedExperiments = getRequestedExperiments(sample);

      const currentLabWips = sampleWips.filter(
        (wip) => normalizeLab(wip.lab_name) === normalizeLab(currentLab)
      );

      const currentLabCompletedWips = currentLabWips.filter(
        (wip) => wip.status === "completed"
      );

      const remainingWips = sampleWips.filter((wip) => wip.status !== "completed");

      const dependencyNextLoaded =
        dependencyNextBySampleKey[dependencyKey] !== undefined;
      const dependencyNext = dependencyNextBySampleKey[dependencyKey] ?? null;

      if (!dependencyNextLoaded) return;
      if (!dependencyNext) return;

      const apiNextLab = dependencyNext.labName?.trim();
      const apiNextExperiment = dependencyNext.experimentName?.trim();

      if (!apiNextLab) return;
      if (normalizeLab(apiNextLab) === normalizeLab(currentLab)) return;

      if (requestedExperiments.length > 0) {
        const unfinishedExperiments = requestedExperiments.filter(
          (experiment) => !isExperimentCompleted(sampleWips, experiment)
        );

        const nextUnlockedExperiments = getNextUnlockedExperiments(
          requestedExperiments,
          sampleWips
        );

        const apiMatchedExperiment = nextUnlockedExperiments.find(
          (experiment) =>
            normalizeLab(experiment.lab_name) === normalizeLab(apiNextLab) &&
            (!apiNextExperiment ||
              normalizeLab(experiment.experiment_item) ===
                normalizeLab(apiNextExperiment))
        );

        const nextExperiment =
          apiMatchedExperiment ??
          unfinishedExperiments.find(
            (experiment) =>
              normalizeLab(experiment.lab_name) === normalizeLab(apiNextLab) &&
              (!apiNextExperiment ||
                normalizeLab(experiment.experiment_item) ===
                  normalizeLab(apiNextExperiment))
          ) ?? {
            lab_name: apiNextLab,
            experiment_item: apiNextExperiment || "未命名實驗",
            targetGroup: dependencyNext.targetGroup || "G1",
            target: dependencyNext.target || 1,
          };

        const nextWip =
          findMatchingWipForExperiment(sampleWips, nextExperiment) ??
          sampleWips.find(
            (wip) =>
              wip.status !== "completed" &&
              normalizeLab(wip.lab_name) === normalizeLab(nextExperiment.lab_name) &&
              normalizeLab(wip.experiment_item ?? "") ===
                normalizeLab(nextExperiment.experiment_item ?? "")
          ) ??
          null;

        const existingTransfer = findExistingBlockingTransfer(
          sample,
          nextWip,
          transfersByTargetId
        );

        result.push({
          kind: "transfer",
          sample,
          currentLabCompletedWips,
          remainingWips,
          remainingExperiments: unfinishedExperiments,
          nextLab: apiNextLab,
          nextExperiment,
          nextWip,
          existingTransfer,
        });

        return;
      }

      const otherLabRemainingWips = remainingWips.filter(
        (wip) => normalizeLab(wip.lab_name) !== normalizeLab(currentLab)
      );

      const apiMatchedWip = otherLabRemainingWips.find(
        (wip) =>
          normalizeLab(wip.lab_name) === normalizeLab(apiNextLab) &&
          (!apiNextExperiment ||
            normalizeLab(wip.experiment_item ?? "") === normalizeLab(apiNextExperiment))
      );

      const nextWip = apiMatchedWip ?? otherLabRemainingWips[0] ?? null;

      const nextExperiment = {
        lab_name: apiNextLab,
        experiment_item:
          apiNextExperiment || nextWip?.experiment_item || "未命名實驗",
      };

      const existingTransfer = findExistingBlockingTransfer(
        sample,
        nextWip,
        transfersByTargetId
      );

      result.push({
        kind: "transfer",
        sample,
        currentLabCompletedWips,
        remainingWips,
        remainingExperiments: [nextExperiment],
        nextLab: apiNextLab,
        nextExperiment,
        nextWip,
        existingTransfer,
      });
    });

    return result;
  }, [
    samples,
    wipsBySampleId,
    transfersByTargetId,
    currentLab,
    displayableTransferSamples,
    dependencyNextBySampleKey,
  ]);


  const sameLabNextCandidates = useMemo<SameLabNextCandidate[]>(() => {
    const result: SameLabNextCandidate[] = [];
    const displayableSampleKeys = new Set(
      displayableTransferSamples.map((sample) => getSampleDependencyKey(sample))
    );

    samples.forEach((sample) => {
      const dependencyKey = getSampleDependencyKey(sample);

      if (!displayableSampleKeys.has(dependencyKey)) return;

      const sampleWips = wipsBySampleId[sample.id] ?? [];
      const requestedExperiments = getRequestedExperiments(sample);

      const currentLabWips = sampleWips.filter(
        (wip) => normalizeLab(wip.lab_name) === normalizeLab(currentLab)
      );

      const currentLabCompletedWips = currentLabWips.filter(
        (wip) => wip.status === "completed"
      );

      const remainingWips = sampleWips.filter((wip) => wip.status !== "completed");

      const dependencyNextLoaded =
        dependencyNextBySampleKey[dependencyKey] !== undefined;
      const dependencyNext = dependencyNextBySampleKey[dependencyKey] ?? null;

      if (!dependencyNextLoaded) return;
      if (!dependencyNext) return;

      const apiNextLab = dependencyNext.labName?.trim();
      const apiNextExperiment = dependencyNext.experimentName?.trim();

      if (!apiNextLab) return;
      if (normalizeLab(apiNextLab) !== normalizeLab(currentLab)) return;

      if (requestedExperiments.length > 0) {
        const unfinishedExperiments = requestedExperiments.filter(
          (experiment) => !isExperimentCompleted(sampleWips, experiment)
        );

        const nextUnlockedExperiments = getNextUnlockedExperiments(
          requestedExperiments,
          sampleWips
        );

        const apiMatchedExperiment = nextUnlockedExperiments.find(
          (experiment) =>
            normalizeLab(experiment.lab_name) === normalizeLab(apiNextLab) &&
            (!apiNextExperiment ||
              normalizeLab(experiment.experiment_item) ===
                normalizeLab(apiNextExperiment))
        );

        const nextExperiment =
          apiMatchedExperiment ??
          unfinishedExperiments.find(
            (experiment) =>
              normalizeLab(experiment.lab_name) === normalizeLab(apiNextLab) &&
              (!apiNextExperiment ||
                normalizeLab(experiment.experiment_item) ===
                  normalizeLab(apiNextExperiment))
          ) ?? {
            lab_name: apiNextLab,
            experiment_item: apiNextExperiment || "未命名實驗",
            targetGroup: dependencyNext.targetGroup || "G1",
            target: dependencyNext.target || 1,
          };

        const nextWip =
          findMatchingWipForExperiment(sampleWips, nextExperiment) ??
          sampleWips.find(
            (wip) =>
              wip.status !== "completed" &&
              normalizeLab(wip.lab_name) === normalizeLab(nextExperiment.lab_name) &&
              normalizeLab(wip.experiment_item ?? "") ===
                normalizeLab(nextExperiment.experiment_item ?? "")
          ) ??
          null;

        result.push({
          sample,
          currentLabCompletedWips,
          remainingWips,
          nextLab: apiNextLab,
          nextExperiment,
          nextWip,
        });

        return;
      }

      const sameLabRemainingWips = remainingWips.filter(
        (wip) => normalizeLab(wip.lab_name) === normalizeLab(currentLab)
      );

      const apiMatchedWip = sameLabRemainingWips.find(
        (wip) =>
          normalizeLab(wip.lab_name) === normalizeLab(apiNextLab) &&
          (!apiNextExperiment ||
            normalizeLab(wip.experiment_item ?? "") === normalizeLab(apiNextExperiment))
      );

      const nextWip = apiMatchedWip ?? sameLabRemainingWips[0] ?? null;

      const nextExperiment = {
        lab_name: apiNextLab,
        experiment_item:
          apiNextExperiment || nextWip?.experiment_item || "未命名實驗",
      };

      result.push({
        sample,
        currentLabCompletedWips,
        remainingWips,
        nextLab: apiNextLab,
        nextExperiment,
        nextWip,
      });
    });

    return result;
  }, [
    samples,
    wipsBySampleId,
    currentLab,
    displayableTransferSamples,
    dependencyNextBySampleKey,
  ]);


  async function fetchDependencyNextForSamples(targetSamples: Sample[]) {
    const uniqueSamples = targetSamples.filter((sample, index, array) => {
      const key = getSampleDependencyKey(sample);
      return array.findIndex((item) => getSampleDependencyKey(item) === key) === index;
    });

    const samplesToFetch = uniqueSamples.filter((sample) => {
      const key = getSampleDependencyKey(sample);
      const cachedNext = dependencyNextBySampleKey[key];
      const selectedCompleted =
        cachedNext !== undefined && isDependencyNextCompleted(sample, cachedNext);

      return (
        (cachedNext === undefined || selectedCompleted) &&
        !dependencyNextLoadingBySampleKey[key]
      );
    });

    if (samplesToFetch.length === 0) return;

    setDependencyNextLoadingBySampleKey((previous) => {
      const next = { ...previous };

      samplesToFetch.forEach((sample) => {
        next[getSampleDependencyKey(sample)] = true;
      });

      return next;
    });

    await Promise.all(
      samplesToFetch.map(async (sample) => {
        const key = getSampleDependencyKey(sample);

        try {
          const response = await apiPost<WipDependencyNextResponse>(
            "/api/wips/dependency/next",
            {
              sampleId: sample.sample_no,
              orderNo: sample.order_no,
            }
          );

          setDependencyNextBySampleKey((previous) => ({
            ...previous,
            [key]: response.data ?? null,
          }));

          setDependencyNextErrorBySampleKey((previous) => ({
            ...previous,
            [key]: "",
          }));
        } catch (err) {
          logClientError("fetchDependencyNextForSamples failed", err);

          setDependencyNextBySampleKey((previous) => ({
            ...previous,
            [key]: null,
          }));

          setDependencyNextErrorBySampleKey((previous) => ({
            ...previous,
            [key]: getErrorMessage(err, "取得下一個交接地點失敗"),
          }));
        } finally {
          setDependencyNextLoadingBySampleKey((previous) => ({
            ...previous,
            [key]: false,
          }));
        }
      })
    );
  }

  useEffect(() => {
    if (displayableTransferSamples.length === 0) return;

    void fetchDependencyNextForSamples(displayableTransferSamples);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [displayableTransferSamples]);

  const isResolvingTransferNextDestination = useMemo(() => {
    return displayableTransferSamples.some((sample) => {
      const key = getSampleDependencyKey(sample);

      return (
        dependencyNextLoadingBySampleKey[key] ||
        (dependencyNextBySampleKey[key] === undefined &&
          !dependencyNextErrorBySampleKey[key])
      );
    });
  }, [
    displayableTransferSamples,
    dependencyNextBySampleKey,
    dependencyNextErrorBySampleKey,
    dependencyNextLoadingBySampleKey,
  ]);

  const transferNextDestinationErrors = useMemo(() => {
    return displayableTransferSamples
      .map((sample) => {
        const key = getSampleDependencyKey(sample);
        return dependencyNextErrorBySampleKey[key];
      })
      .filter(Boolean);
  }, [displayableTransferSamples, dependencyNextErrorBySampleKey]);

  const returnCandidates = useMemo<ReturnCandidate[]>(() => {
    const result: ReturnCandidate[] = [];

    samples.forEach((sample) => {
      const sampleWips = wipsBySampleId[sample.id] ?? [];

      if (sample.status === "picked_up") return;
      if (sample.status === "outbound") return;
      if (sample.status === "pending_receive") return;

      const requestedExperiments = getRequestedExperiments(sample);

      const currentLabWips = sampleWips.filter(
        (wip) => normalizeLab(wip.lab_name) === normalizeLab(currentLab)
      );

      if (currentLabWips.length === 0) return;

      const currentLabIncompleteWips = currentLabWips.filter((wip) => wip.status !== "completed");

      if (currentLabIncompleteWips.length > 0) return;

      const currentLabCompletedWips = currentLabWips.filter((wip) => wip.status === "completed");

      const unfinishedAnyWips = sampleWips.filter((wip) => wip.status !== "completed");

      if (unfinishedAnyWips.length > 0) return;

      if (requestedExperiments.length > 0) {
        const unfinishedExperiments = requestedExperiments.filter(
          (experiment) => !isExperimentCompleted(sampleWips, experiment)
        );

        if (unfinishedExperiments.length > 0) return;

        const currentLabLastIndex = requestedExperiments.reduce((lastIndex, experiment, index) => {
          if (normalizeLab(experiment.lab_name) === normalizeLab(currentLab)) {
            return index;
          }

          return lastIndex;
        }, -1);

        if (currentLabLastIndex >= 0 && currentLabLastIndex !== requestedExperiments.length - 1) {
          return;
        }

        result.push({
          kind: "return",
          sample,
          currentLabCompletedWips,
          allWips: sampleWips,
        });

        return;
      }

      if (sampleWips.length === 0) return;

      result.push({
        kind: "return",
        sample,
        currentLabCompletedWips,
        allWips: sampleWips,
      });
    });

    return result;
  }, [samples, wipsBySampleId, currentLab]);

  const pickupCandidates = useMemo<ReturnCandidate[]>(() => {
    const result: ReturnCandidate[] = [];

    samples.forEach((sample) => {
      const sampleWips = wipsBySampleId[sample.id] ?? [];

      if (sample.status !== "outbound") return;

      const currentLabWips = sampleWips.filter(
        (wip) => normalizeLab(wip.lab_name) === normalizeLab(currentLab)
      );

      if (currentLabWips.length === 0) return;

      result.push({
        kind: "return",
        sample,
        currentLabCompletedWips: currentLabWips.filter((wip) => wip.status === "completed"),
        allWips: sampleWips,
      });
    });

    return result;
  }, [samples, wipsBySampleId, currentLab]);

  const candidates = useMemo<Candidate[]>(() => {
    return [...transferCandidates, ...returnCandidates, ...pickupCandidates];
  }, [transferCandidates, returnCandidates, pickupCandidates]);

  const selectedCandidate = useMemo(() => {
    return (
      candidates.find((candidate) => getCandidateKey(candidate) === selectedCandidateKey) ?? null
    );
  }, [candidates, selectedCandidateKey]);

  async function loadData(options?: { resetCandidate?: boolean }) {
    if (!currentUser) {
      setLoading(false);
      return;
    }

    const resetCandidate = options?.resetCandidate ?? true;

    try {
      setLoading(true);
      setError("");
      setSuccessMessage("");

      const [sampleData, wipData, transferData] = await Promise.all([
        apiGet<Sample[]>("/api/samples"),
        apiGet<Wip[]>("/api/wips?include_all_for_flow=true"),
        apiGet<Transfer[]>("/api/transfers"),
      ]);

      setSamples(sampleData);
      setWips(wipData);
      setTransfers(transferData);

      if (resetCandidate) {
        setSelectedCandidateKey("");
      }

      if (
        selectedTransferId &&
        !transferData.some((transfer) => transfer.id === selectedTransferId)
      ) {
        setSelectedTransferId(null);
      }
    } catch (err) {
      setError(getErrorMessage(err, "載入樣品流轉資料失敗"));
    } finally {
      setLoading(false);
    }
  }

  async function createTransfer(candidate: TransferCandidate) {
    try {
      setSubmitting(true);
      setError("");
      setSuccessMessage("");

      await apiPost("/api/transfers", {
        target_type: "sample",
        target_id: candidate.sample.id,
        order_no: candidate.sample.order_no,
        sample_no: candidate.sample.sample_no,
        wip_no: candidate.nextWip?.wip_no ?? null,
        from_lab: currentLab,
        to_lab: candidate.nextLab,
        handed_by: operatorName,
        note: candidate.nextWip
          ? `目前 ${currentLab} 的 WIP 已完成，交接至 ${candidate.nextLab} 收樣區。下一個 WIP：${candidate.nextWip.wip_no}`
          : `目前 ${currentLab} 的 WIP 已完成，交接至 ${candidate.nextLab} 收樣區。下一個測驗：${candidate.nextExperiment.experiment_item}。`,
      });

      setSuccessMessage("交接申請已建立");
      await loadData();
    } catch (err) {
      logClientError("createTransfer failed", err);
      setError(getErrorMessage(err, "建立交接申請失敗"));
    } finally {
      setSubmitting(false);
    }
  }

  async function sendTransfer(transfer: Transfer) {
    try {
      setSubmitting(true);
      setError("");
      setSuccessMessage("");

      await apiPost(`/api/transfers/${transfer.id}/actions`, {
        action: "send",
        operator_name: operatorName,
      });

      setSelectedTransferId(null);
      setSuccessMessage("已送出交接，樣品已移至下一個 Lab 的待收樣區");
      await loadData();
    } catch (err) {
      logClientError("sendTransfer failed", err);
      setError(getErrorMessage(err, "送出交接單失敗"));
    } finally {
      setSubmitting(false);
    }
  }

  async function cancelTransfer(transfer: Transfer) {
    try {
      setSubmitting(true);
      setError("");
      setSuccessMessage("");

      await apiPost(`/api/transfers/${transfer.id}/actions`, {
        action: "cancel",
        operator_name: operatorName,
      });

      setSelectedTransferId(null);
      setSuccessMessage("交接單已取消");
      await loadData();
    } catch (err) {
      logClientError("cancelTransfer failed", err);
      setError(getErrorMessage(err, "取消交接單失敗"));
    } finally {
      setSubmitting(false);
    }
  }

  async function notifyPickup(candidate: ReturnCandidate) {
    try {
      setSubmitting(true);
      setError("");
      setSuccessMessage("");

      await apiPost(`/api/samples/${candidate.sample.id}/actions`, {
        action: "outbound",
        operator_name: operatorName,
        current_location: `${currentLab} 待取件區`,
        note: candidate.sample.note,
        confirm_notify_pickup: true,
      });

      setSelectedTransferId(null);
      setSuccessMessage("已通知原使用者取件，樣品已移至待取件區");
      await loadData();
    } catch (err) {
      logClientError("notifyPickup failed", err);
      setError(getErrorMessage(err, "通知取件失敗"));
    } finally {
      setSubmitting(false);
    }
  }

  // confirmPickup removed: pickup_confirmed is reserved for the original
  // requester (backend _validate_sample_action_permission). The
  // /sample page (我的樣品追蹤) shows the user-facing button. /transfer
  // only shows status while the lab waits.

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentUser?.id, currentUser?.role, currentUser?.lab_name]);

  if (authLoading || masterQuery.isLoading) {
    return (
      <section style={panelStyle}>
        <div style={emptyStyle}>載入中...</div>
      </section>
    );
  }

  if (!currentUser) {
    return (
      <section style={panelStyle}>
        <div style={emptyStyle}>尚未取得登入身分</div>
      </section>
    );
  }

  return (
    <div>
      <div style={headerStyle}>
        <div>
          <h1 style={titleStyle}>樣品交付管理</h1>
          <p style={subtitleStyle}>
            TRANSFER OUT · 目前 Lab：{currentLab} ·
            這裡負責建立交接、送出交接，以及查看我方相關交接狀態。
          </p>
        </div>

        <div style={headerActionsStyle}>
          <button onClick={() => (window.location.href = "/sample")} style={secondaryButtonStyle}>
            回樣品管理
          </button>
          <button onClick={() => loadData()} style={secondaryButtonStyle}>
            重新整理
          </button>
        </div>
      </div>

      <div style={currentUserBoxStyle}>
        <div style={currentUserTitleStyle}>目前操作身分</div>
        <div style={currentUserTextStyle}>
          {currentUser.name} · {currentUser.role_name ?? currentUser.role} · {currentLab}
        </div>
      </div>

      {error && <div style={errorStyle}>{error}</div>}
      {successMessage && <div style={successStyle}>{successMessage}</div>}

      <section style={summaryGridStyle}>
        <SummaryCard label="待續行實驗" value={sameLabNextCandidates.length} />
        <SummaryCard label="可交接" value={transferCandidates.length} />
        <SummaryCard
          label="我方已建申請"
          value={
            transfers.filter(
              (transfer) =>
                normalizeLab(transfer.from_lab) === normalizeLab(currentLab) &&
                transfer.status === "pending"
            ).length
          }
        />
        <SummaryCard
          label="待我方收樣"
          value={
            transfers.filter(
              (transfer) =>
                normalizeLab(transfer.to_lab) === normalizeLab(currentLab) &&
                transfer.status === "transferring"
            ).length
          }
        />
        <SummaryCard label="待通知取件" value={returnCandidates.length} />
        <SummaryCard label="待取件" value={pickupCandidates.length} />
      </section>

      <section style={twoColumnGridStyle}>
        <div style={panelStyle}>
          <div style={panelHeaderStyle}>
            <div>
              <div style={panelTitleStyle}>待續行實驗</div>
              <div style={hintStyle}>
                已完成目前作業階段，後續仍有實驗需於本 Lab 接續處理。
              </div>
            </div>

            <span style={countBadgeStyle}>{sameLabNextCandidates.length} 筆</span>
          </div>

          {loading ? (
            <div style={emptyStyle}>載入中...</div>
          ) : isResolvingTransferNextDestination ? (
            <div style={emptyStyle}>更新作業狀態中...</div>
          ) : sameLabNextCandidates.length === 0 ? (
            <div style={emptyStyle}>目前沒有待續行實驗的樣品。</div>
          ) : (
            <div style={candidateListStyle}>
              {sameLabNextCandidates.map((candidate) => {
                const key = `same-lab-${candidate.sample.id}-${candidate.nextWip?.id ?? candidate.nextExperiment.experiment_item}`;

                return (
                  <div key={key} style={candidateCardStyle}>
                    <div style={candidateTopRowStyle}>
                      <div>
                        <div style={candidateTitleStyle}>{candidate.sample.sample_no}</div>
                        <div style={candidateSubtitleStyle}>
                          {candidate.sample.sample_name ?? "未命名樣品"} ·{" "}
                          {candidate.sample.order_no}
                        </div>
                      </div>

                      <span style={warningBadgeStyle}>待續行</span>
                    </div>

                    <div style={candidateMetaGridStyle}>
                      <InfoLine label="目前位置" value={candidate.sample.current_location ?? "-"} />
                      <InfoLine
                        label="下一實驗"
                        value={`${candidate.nextLab} · ${candidate.nextExperiment.experiment_item}`}
                      />
                      <InfoLine
                        label="WIP 狀態"
                        value={candidate.nextWip?.wip_no ?? "尚未建立"}
                      />
                      <InfoLine label="作業狀態" value="待本 Lab 接續處理" />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div style={panelStyle}>
          <div style={panelHeaderStyle}>
            <div>
              <div style={panelTitleStyle}>可交接</div>
              <div style={hintStyle}>
                目前階段已完成，可建立交接並送往下一個 Lab。
              </div>
            </div>

            <span style={countBadgeStyle}>
              {transferCandidates.length} 筆
            </span>
          </div>

          {loading ? (
            <div style={emptyStyle}>載入中...</div>
          ) : isResolvingTransferNextDestination ? (
            <div style={emptyStyle}>取得下一個交付地點中...</div>
          ) : transferCandidates.length === 0 ? (
            <div style={emptyStyle}>
              {transferNextDestinationErrors.length > 0
                ? transferNextDestinationErrors[0]
                : "目前沒有可交接的樣品。"}
            </div>
          ) : (
            <div style={candidateListStyle}>
              {transferCandidates.map((candidate) => {
                const candidateKey = getCandidateKey(candidate);
                const selected = selectedCandidateKey === candidateKey;
                const dependencyKey = getSampleDependencyKey(candidate.sample);
                const isLoadingNext = dependencyNextLoadingBySampleKey[dependencyKey];
                const nextError = dependencyNextErrorBySampleKey[dependencyKey];

                return (
                  <button
                    key={candidateKey}
                    type="button"
                    onClick={() => setSelectedCandidateKey(candidateKey)}
                    style={selected ? selectedCandidateCardStyle : candidateCardStyle}
                  >
                    <div style={candidateTopRowStyle}>
                      <div>
                        <div style={candidateTitleStyle}>{candidate.sample.sample_no}</div>
                        <div style={candidateSubtitleStyle}>
                          {candidate.sample.sample_name ?? "未命名樣品"} ·{" "}
                          {candidate.sample.order_no}
                        </div>
                      </div>

                      {candidate.existingTransfer ? (
                        <StatusBadge status={candidate.existingTransfer.status} />
                      ) : (
                        <span style={readyBadgeStyle}>可建立</span>
                      )}
                    </div>

                    <div style={candidateMetaGridStyle}>
                      <InfoLine label="目前位置" value={candidate.sample.current_location ?? "-"} />
                      <InfoLine
                        label="目前完成"
                        value={`${currentLab} · ${candidate.currentLabCompletedWips.length} 個 WIP`}
                      />
                      <InfoLine
                        label="送往"
                        value={
                          isLoadingNext
                            ? "取得下一站中..."
                            : `${candidate.nextLab} 收樣區`
                        }
                      />
                      <InfoLine
                        label="下一實驗"
                        value={`${candidate.nextLab} · ${candidate.nextExperiment.experiment_item}`}
                      />
                      <InfoLine
                        label="WIP 狀態"
                        value={candidate.nextWip?.wip_no ?? "尚未建立"}
                      />
                      {nextError && <InfoLine label="下一站錯誤" value={nextError} />}
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        <div style={panelStyle}>
          <div style={panelHeaderStyle}>
            <div>
              <div style={panelTitleStyle}>待通知取件</div>
              <div style={hintStyle}>實驗流程已完成，可通知申請人取件。</div>
            </div>

            <span style={countBadgeStyle}>{returnCandidates.length} 筆</span>
          </div>

          {loading ? (
            <div style={emptyStyle}>載入中...</div>
          ) : returnCandidates.length === 0 ? (
            <div style={emptyStyle}>目前沒有待通知取件的樣品。</div>
          ) : (
            <div style={candidateListStyle}>
              {returnCandidates.map((candidate) => {
                const candidateKey = getCandidateKey(candidate);
                const selected = selectedCandidateKey === candidateKey;

                return (
                  <button
                    key={candidateKey}
                    type="button"
                    onClick={() => setSelectedCandidateKey(candidateKey)}
                    style={selected ? selectedCandidateCardStyle : candidateCardStyle}
                  >
                    <div style={candidateTopRowStyle}>
                      <div>
                        <div style={candidateTitleStyle}>{candidate.sample.sample_no}</div>
                        <div style={candidateSubtitleStyle}>
                          {candidate.sample.sample_name ?? "未命名樣品"} ·{" "}
                          {candidate.sample.order_no}
                        </div>
                      </div>

                      <span style={readyBadgeStyle}>待通知</span>
                    </div>

                    <div style={candidateMetaGridStyle}>
                      <InfoLine label="目前位置" value={candidate.sample.current_location ?? "-"} />
                      <InfoLine
                        label="樣品狀態"
                        value={sampleStatusText[candidate.sample.status] ?? candidate.sample.status}
                      />
                      <InfoLine label="申請人" value={candidate.sample.applicant_name ?? "-"} />
                      <InfoLine
                        label="完成 WIP"
                        value={`${candidate.allWips.filter((wip) => wip.status === "completed").length} / ${candidate.allWips.length}`}
                      />
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        <div style={panelStyle}>
          <div style={panelHeaderStyle}>
            <div>
              <div style={panelTitleStyle}>待取件</div>
              <div style={hintStyle}>已通知申請人取件，樣品等待取回中。</div>
            </div>

            <span style={countBadgeStyle}>{pickupCandidates.length} 筆</span>
          </div>

          {loading ? (
            <div style={emptyStyle}>載入中...</div>
          ) : pickupCandidates.length === 0 ? (
            <div style={emptyStyle}>目前沒有待取件的樣品。</div>
          ) : (
            <div style={candidateListStyle}>
              {pickupCandidates.map((candidate) => {
                const candidateKey = getCandidateKey(candidate);
                const selected = selectedCandidateKey === candidateKey;

                return (
                  <button
                    key={candidateKey}
                    type="button"
                    onClick={() => setSelectedCandidateKey(candidateKey)}
                    style={selected ? selectedCandidateCardStyle : candidateCardStyle}
                  >
                    <div style={candidateTopRowStyle}>
                      <div>
                        <div style={candidateTitleStyle}>{candidate.sample.sample_no}</div>
                        <div style={candidateSubtitleStyle}>
                          {candidate.sample.sample_name ?? "未命名樣品"} ·{" "}
                          {candidate.sample.order_no}
                        </div>
                      </div>

                      <span style={warningBadgeStyle}>待取件</span>
                    </div>

                    <div style={candidateMetaGridStyle}>
                      <InfoLine label="目前位置" value={candidate.sample.current_location ?? "-"} />
                      <InfoLine
                        label="樣品狀態"
                        value={sampleStatusText[candidate.sample.status] ?? candidate.sample.status}
                      />
                      <InfoLine label="申請人" value={candidate.sample.applicant_name ?? "-"} />
                      <InfoLine
                        label="完成 WIP"
                        value={`${candidate.allWips.filter((wip) => wip.status === "completed").length} / ${candidate.allWips.length}`}
                      />
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </section>

      <section style={panelStyle}>
        <div style={panelHeaderStyle}>
          <div>
            <div style={panelTitleStyle}>交接 / 取件操作</div>
            <div style={hintStyle}>
              選擇上方樣品後，建立交接、送出到下一個 Lab 待收樣區，或通知使用者取件。
            </div>
          </div>
        </div>

        {!selectedCandidate ? (
          <div style={emptyStyle}>請先選擇上方任一樣品。</div>
        ) : selectedCandidate.kind === "transfer" ? (
          <TransferDetail
            candidate={selectedCandidate}
            currentLab={currentLab}
            submitting={submitting}
            onCreateTransfer={createTransfer}
            onSendTransfer={sendTransfer}
            onCancelTransfer={cancelTransfer}
          />
        ) : (
          <ReturnDetail
            candidate={selectedCandidate}
            submitting={submitting}
            onNotifyPickup={notifyPickup}
          />
        )}
      </section>

      <section style={panelStyle}>
        <div style={panelHeaderStyle}>
          <div>
            <div style={panelTitleStyle}>我方相關交接單列表</div>
            <div style={hintStyle}>
              顯示我方送出的交接單，以及其他 Lab 交給我方的待收樣 / 已收樣交接單。
            </div>
          </div>

          <span style={countBadgeStyle}>{transfers.length} 筆</span>
        </div>

        {transfers.length === 0 ? (
          <div style={emptyStyle}>目前沒有交接單。</div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={tableStyle}>
              <thead>
                <tr style={{ background: "var(--s2)" }}>
                  {["交接單", "樣品", "From", "To", "狀態", "交接人", "簽收人", "操作"].map(
                    (header) => (
                      <th key={header} style={thStyle}>
                        {header}
                      </th>
                    )
                  )}
                </tr>
              </thead>

              <tbody>
                {transfers.map((transfer) => (
                  <tr key={transfer.id} style={{ borderBottom: "1px solid var(--border2)" }}>
                    <td style={monoTdStyle}>{transfer.transfer_no ?? transfer.id.slice(0, 8)}</td>
                    <td style={monoTdStyle}>{transfer.sample_no ?? "-"}</td>
                    <td style={tdStyle}>{transfer.from_lab ?? "-"}</td>
                    <td style={tdStyle}>{transfer.to_lab ?? "-"}</td>
                    <td style={tdStyle}>
                      <span style={statusBadgeStyle}>{getTransferStatusText(transfer)}</span>
                    </td>
                    <td style={tdStyle}>{transfer.handed_by ?? "-"}</td>
                    <td style={tdStyle}>{transfer.received_by ?? "-"}</td>
                    <td style={tdStyle}>
                      <div style={smallActionGroupStyle}>
                        <button
                          type="button"
                          onClick={() => setSelectedTransferId(transfer.id)}
                          style={smallSecondaryButtonStyle}
                        >
                          查看
                        </button>

                        {isOutgoingTransfer(transfer) && transfer.status === "pending" && (
                          <button
                            type="button"
                            onClick={() => sendTransfer(transfer)}
                            disabled={submitting}
                            style={smallPrimaryButtonStyle}
                          >
                            送出
                          </button>
                        )}

                        {isOutgoingTransfer(transfer) && transfer.status === "pending" && (
                          <button
                            type="button"
                            onClick={() => cancelTransfer(transfer)}
                            disabled={submitting}
                            style={smallDangerButtonStyle}
                          >
                            取消
                          </button>
                        )}

                        {getTransferActionHint(transfer) && (
                          <span style={hintStyle}>{getTransferActionHint(transfer)}</span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {selectedTransfer && (
        <TransferModal
          transfer={selectedTransfer}
          currentLab={currentLab}
          submitting={submitting}
          onClose={() => setSelectedTransferId(null)}
          onSendTransfer={sendTransfer}
          onCancelTransfer={cancelTransfer}
        />
      )}
    </div>
  );
}
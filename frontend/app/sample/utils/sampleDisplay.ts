import { sampleStatusText } from "../constants";
import { formatExperimentSummary } from "@/lib/experimentSummary";
import type { CurrentUser, Sample, SampleFilter, Transfer } from "../types";

export function isSystemAdmin(user: CurrentUser) {
  return user.role === "system_admin";
}

export function isLabUser(user: CurrentUser) {
  return ["lab_engineer", "lab_supervisor"].includes(user.role);
}

export function isFactoryUser(user: CurrentUser) {
  return user.role === "plant_user";
}

export function getRoleLabel(user: CurrentUser) {
  if (user.role_name) return user.role_name;

  const roleLabelMap: Record<string, string> = {
    system_admin: "系統管理者",
    lab_supervisor: "實驗室主管",
    lab_engineer: "實驗室人員",
    plant_user: "廠區使用者",
  };

  return roleLabelMap[user.role] ?? user.role ?? "未知角色";
}

export function getUserLab(user: CurrentUser) {
  return user.lab_name ?? user.department ?? "";
}

export function isActiveSampleStatus(status: Sample["status"]) {
  return !["outbound", "picked_up", "lost", "damaged", "cancelled"].includes(status);
}

function normalizeLocationText(value: string) {
  return value.replace(/\s+/g, "").toLowerCase();
}

export function isSampleInCurrentLab(sample: Sample | null | undefined, user: CurrentUser) {
  if (!sample || !isLabUser(user)) return false;

  const currentLab = getUserLab(user);
  if (!currentLab) return false;

  const location = sample.current_location ?? "";
  if (!location) return false;

  // 樣品是否還在本 Lab，應以目前位置判斷，不應只用 pending_transfer 狀態判斷。
  // pending_transfer 代表「可交接但尚未送出」，只要位置仍是本 Lab 的暫存 / 待送區，就仍視為在本 Lab。
  return normalizeLocationText(location).startsWith(normalizeLocationText(currentLab));
}

export function shouldMaskSampleForLab(sample: Sample, user: CurrentUser) {
  if (!isLabUser(user)) return false;
  if (["picked_up", "lost", "damaged", "cancelled"].includes(sample.status)) return false;
  if (sample.status === "pending_transfer") return false;

  return !isSampleInCurrentLab(sample, user);
}

function shouldUseOutgoingTransferView(
  sample: Sample,
  user: CurrentUser,
  outgoingTransfer?: Transfer
) {
  if (!outgoingTransfer || !isLabUser(user)) return false;

  const currentLab = getUserLab(user);
  if (!currentLab || outgoingTransfer.from_lab !== currentLab) return false;

  return !isSampleInCurrentLab(sample, user);
}

function getTransferDisplayStatus(transfer?: Transfer) {
  if (!transfer) return "transferred_out";

  if (transfer.status === "pending") return "transfer_pending";
  if (transfer.status === "transferring") return "transferred_waiting_receive";
  if (transfer.status === "received") return "transferred_received";
  if (transfer.status === "cancelled") return "cancelled";

  return "transferred_out";
}

function getTransferDisplayLocation(transfer?: Transfer) {
  if (!transfer) return "已離開本實驗室";

  if (transfer.status === "pending") return "本實驗室交接待送區";
  if (transfer.status === "transferring") {
    return transfer.to_lab
      ? `已送出，等待接收實驗室（${transfer.to_lab}）收樣`
      : "已送出，等待接收實驗室收樣";
  }

  if (transfer.status === "received") {
    return transfer.to_lab ? `已由接收實驗室（${transfer.to_lab}）收樣` : "已由接收實驗室收樣";
  }

  if (transfer.status === "cancelled") return "交接已取消";

  return "已離開本實驗室";
}

export function isSampleVisibleForUser(sample: Sample, user: CurrentUser) {
  if (isSystemAdmin(user)) return true;

  if (isFactoryUser(user)) {
    return sample.applicant_name === user.name;
  }

  if (isLabUser(user)) {
    return Boolean(getUserLab(user));
  }

  return false;
}

export function normalizeSampleFilter(user: CurrentUser, filter: SampleFilter): SampleFilter {
  if (isFactoryUser(user)) {
    return filter === "current" ? "all" : filter;
  }

  if (isLabUser(user)) {
    return filter === "active" ? "current" : filter;
  }

  return filter;
}

export function filterSamplesByView(samples: Sample[], user: CurrentUser, filter: SampleFilter) {
  const normalizedFilter = normalizeSampleFilter(user, filter);
  const visibleSamples = samples.filter((sample) => isSampleVisibleForUser(sample, user));

  if (isFactoryUser(user)) {
    if (normalizedFilter === "active") {
      return visibleSamples.filter((sample) => isActiveSampleStatus(sample.status));
    }

    if (normalizedFilter === "outbound") {
      return visibleSamples.filter((sample) => sample.status === "outbound");
    }

    if (normalizedFilter === "picked_up") {
      return visibleSamples.filter((sample) => sample.status === "picked_up");
    }

    return visibleSamples;
  }

  if (isLabUser(user)) {
    if (normalizedFilter === "current") {
      return visibleSamples.filter((sample) => isSampleInCurrentLab(sample, user));
    }

    if (normalizedFilter === "outbound") {
      return visibleSamples.filter(
        (sample) => sample.status === "outbound" && isSampleInCurrentLab(sample, user)
      );
    }

    if (normalizedFilter === "picked_up") {
      return visibleSamples.filter((sample) => sample.status === "picked_up");
    }

    return visibleSamples;
  }

  return visibleSamples;
}

export function getDisplaySampleStatus(
  sample: Sample,
  user: CurrentUser,
  outgoingTransfer?: Transfer
) {
  if (shouldUseOutgoingTransferView(sample, user, outgoingTransfer)) {
    return getTransferDisplayStatus(outgoingTransfer);
  }

  if (["picked_up", "lost", "damaged", "cancelled"].includes(sample.status)) {
    return sample.status;
  }

  if (!shouldMaskSampleForLab(sample, user)) {
    return sample.status;
  }

  return getTransferDisplayStatus(outgoingTransfer);
}

export function getDisplaySampleLocation(
  sample: Sample,
  user: CurrentUser,
  outgoingTransfer?: Transfer
) {
  if (shouldUseOutgoingTransferView(sample, user, outgoingTransfer)) {
    return getTransferDisplayLocation(outgoingTransfer);
  }

  if (sample.status === "picked_up") return sample.current_location ?? "已由使用者取回";
  if (sample.status === "cancelled") return "流程已取消";
  if (sample.status === "lost") return "樣品異常：遺失";
  if (sample.status === "damaged") return "樣品異常：破損";

  if (!shouldMaskSampleForLab(sample, user)) {
    return sample.current_location ?? "-";
  }

  return getTransferDisplayLocation(outgoingTransfer);
}

export function formatDateTime(value: string | null | undefined) {
  if (!value) return "-";

  try {
    return new Date(value).toLocaleString("zh-TW", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return value;
  }
}

export function formatStatusChange(fromStatus: string | null, toStatus: string | null) {
  if (!fromStatus && !toStatus) return "狀態未變更";

  const fromText = fromStatus ? (sampleStatusText[fromStatus] ?? fromStatus) : "無";
  const toText = toStatus ? (sampleStatusText[toStatus] ?? toStatus) : "無";

  return `${fromText} → ${toText}`;
}

export function formatSampleExperimentRequirement(experimentItem: string | null | undefined) {
  return formatExperimentSummary(experimentItem);
}

import type { CurrentUser, RequestedExperiment, Sample, Wip, WipForm } from "../types";

export function createEmptyWipForm(labName = ""): WipForm {
  return {
    lab_name: labName,
    experiment_item: "",
    priority: "normal",
    note: "",
    auto_generated: false,
  };
}

export function getCurrentLab(user: CurrentUser | null) {
  return user?.lab_name || user?.department || "";
}

export function parseExperimentsFromSummary(summary: string | null): RequestedExperiment[] {
  if (!summary) return [];

  return summary
    .split("、")
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => {
      const [labName, ...rest] = part.split(":");
      const experimentItem = rest.join(":").trim();

      if (!labName || !experimentItem) return null;

      return {
        lab_name: labName.trim(),
        experiment_item: experimentItem,
      };
    })
    .filter((item): item is RequestedExperiment => Boolean(item));
}

export function getRequestedExperiments(sample: Sample | null): RequestedExperiment[] {
  if (!sample) return [];

  // note 是使用者備註，不解析。
  // 實驗需求統一從 sample.experiment_item 解析。
  return parseExperimentsFromSummary(sample.experiment_item);
}

export function getSampleDefaultPriority() {
  // 不再從 sample.note 取 priority。
  // 備註只給使用者填文字，WIP 預設 normal。
  return "normal";
}

export function makeAutoFormsForSample(
  sample: Sample | null,
  currentLab: string,
  existingWips: Wip[]
) {
  if (!sample) return [createEmptyWipForm(currentLab)];

  const requestedExperiments = getRequestedExperiments(sample);
  const defaultPriority = getSampleDefaultPriority();

  const sampleWips = existingWips
    .filter((wip) => wip.sample_id === sample.id)
    .sort((first, second) => {
      const firstTime = new Date(first.created_at ?? "").getTime();
      const secondTime = new Date(second.created_at ?? "").getTime();

      if (Number.isFinite(firstTime) && Number.isFinite(secondTime) && firstTime !== secondTime) {
        return firstTime - secondTime;
      }

      return String(first.wip_no ?? first.id).localeCompare(String(second.wip_no ?? second.id));
    });

  const unusedWips = [...sampleWips];
  let segmentLab = "";
  let segmentStarted = false;
  const notYetCreated: RequestedExperiment[] = [];

  for (const item of requestedExperiments) {
    const existingIndex = unusedWips.findIndex(
      (wip) => wip.lab_name === item.lab_name && wip.experiment_item === item.experiment_item
    );
    const existingWip = existingIndex === -1 ? null : unusedWips.splice(existingIndex, 1)[0];

    if (!segmentStarted) {
      if (existingWip?.status === "completed") continue;

      segmentStarted = true;
      segmentLab = item.lab_name;
    }

    if (item.lab_name !== segmentLab) break;

    if (!existingWip) {
      notYetCreated.push(item);
    }
  }

  if (segmentLab !== currentLab || notYetCreated.length === 0) {
    return [createEmptyWipForm(currentLab)];
  }

  return notYetCreated.map((item) => ({
    lab_name: item.lab_name,
    experiment_item: item.experiment_item,
    priority: defaultPriority,
    note: "由委託單實驗需求自動帶入",
    auto_generated: true,
  }));
}

export function formatRequestedExperiments(sample: Sample | null) {
  const requestedExperiments = getRequestedExperiments(sample);

  if (requestedExperiments.length === 0) {
    return sample?.experiment_item ?? "-";
  }

  return requestedExperiments.map((item) => `${item.lab_name}:${item.experiment_item}`).join("、");
}

export function shouldOpenCreateWipByDefault(sample: Sample | null) {
  if (!sample) return true;

  if (sample.status === "split") return false;

  return true;
}

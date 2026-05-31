import { formatExperimentSummary, stripExperimentRoutePrefix } from "@/lib/experimentSummary";
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

function normalize(value: string | null | undefined) {
  return (value ?? "").trim().toLowerCase();
}

function isSameLab(left: string | null | undefined, right: string | null | undefined) {
  return normalize(left) === normalize(right);
}

function isSameExperiment(left: string | null | undefined, right: string | null | undefined) {
  return normalize(left) === normalize(right);
}

function parseRoutePrefix(routePrefix: string | undefined, fallbackIndex: number) {
  const fallback = {
    targetGroup: "G1",
    target: fallbackIndex + 1,
  };

  if (!routePrefix) return fallback;

  const [rawGroup, rawTarget] = routePrefix.includes("#")
    ? routePrefix.split("#", 2)
    : [routePrefix, "1"];

  const target = Number(rawTarget);

  return {
    targetGroup: rawGroup.trim() || fallback.targetGroup,
    target: Number.isFinite(target) ? target : fallback.target,
  };
}

export function parseExperimentsFromSummary(summary: string | null): RequestedExperiment[] {
  if (!summary) return [];

  return summary
    .split("、")
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part, index) => {
      const { value: experimentPart, route_prefix: routePrefix } = stripExperimentRoutePrefix(part);
      const separatorIndex = experimentPart.indexOf(":");

      if (separatorIndex === -1) return null;

      const labName = experimentPart.slice(0, separatorIndex).trim();
      const experimentItem = experimentPart.slice(separatorIndex + 1).trim();

      if (!labName || !experimentItem) return null;

      const route = parseRoutePrefix(routePrefix, index);

      return {
        lab_name: labName,
        experiment_item: experimentItem,
        targetGroup: route.targetGroup,
        target: route.target,
      };
    })
    .filter((experiment): experiment is RequestedExperiment => Boolean(experiment));
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

function getExperimentGroup(experiment: RequestedExperiment) {
  return experiment.targetGroup || "G1";
}

function getExperimentTarget(experiment: RequestedExperiment) {
  const target = Number(experiment.target ?? 1);
  return Number.isFinite(target) ? target : 1;
}

function findMatchingWipForExperiment(sampleWips: Wip[], experiment: RequestedExperiment) {
  return (
    sampleWips.find(
      (wip) =>
        isSameLab(wip.lab_name, experiment.lab_name) &&
        isSameExperiment(wip.experiment_item, experiment.experiment_item)
    ) ?? null
  );
}

function isExperimentCompleted(sampleWips: Wip[], experiment: RequestedExperiment) {
  return sampleWips.some(
    (wip) =>
      isSameLab(wip.lab_name, experiment.lab_name) &&
      isSameExperiment(wip.experiment_item, experiment.experiment_item) &&
      wip.status === "completed"
  );
}

export function makeAutoFormsForSample(
  sample: Sample | null,
  currentLab: string,
  existingWips: Wip[]
) {
  if (!sample) return [createEmptyWipForm(currentLab)];

  const requestedExperiments = getRequestedExperiments(sample);
  const defaultPriority = getSampleDefaultPriority();

  const sampleWips = existingWips.filter((wip) => wip.sample_id === sample.id);
  const groups = new Map<
    string,
    Array<{
      experiment: RequestedExperiment;
      index: number;
    }>
  >();

  requestedExperiments.forEach((experiment, index) => {
    const group = getExperimentGroup(experiment);

    if (!groups.has(group)) {
      groups.set(group, []);
    }

    groups.get(group)!.push({ experiment, index });
  });

  const notYetCreated: RequestedExperiment[] = [];

  Array.from(groups.values()).forEach((groupExperiments) => {
    const orderedExperiments = [...groupExperiments].sort((left, right) => {
      const targetDiff = getExperimentTarget(left.experiment) - getExperimentTarget(right.experiment);

      if (targetDiff !== 0) return targetDiff;

      return left.index - right.index;
    });

    const firstUnfinishedIndex = orderedExperiments.findIndex(
      ({ experiment }) => !isExperimentCompleted(sampleWips, experiment)
    );

    if (firstUnfinishedIndex === -1) return;

    const firstUnfinished = orderedExperiments[firstUnfinishedIndex]?.experiment;

    if (!firstUnfinished || !isSameLab(firstUnfinished.lab_name, currentLab)) return;

    for (let index = firstUnfinishedIndex; index < orderedExperiments.length; index += 1) {
      const experiment = orderedExperiments[index].experiment;

      if (!isSameLab(experiment.lab_name, currentLab)) break;

      const existingWip = findMatchingWipForExperiment(sampleWips, experiment);

      if (!existingWip) {
        notYetCreated.push(experiment);
      }
    }
  });

  if (notYetCreated.length === 0) {
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

  return formatExperimentSummary(sample?.experiment_item);
}

export function shouldOpenCreateWipByDefault(sample: Sample | null) {
  if (!sample) return true;

  if (sample.status === "split") return false;

  return true;
}

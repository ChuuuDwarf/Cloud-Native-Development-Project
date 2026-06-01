import { parseExperimentSummary, stripExperimentRoutePrefix } from "@/lib/experimentSummary";
import type { Candidate, RequestedExperiment, Sample, Wip } from "../types";

export function normalizeLab(value: string | null | undefined) {
  return (value ?? "").trim().toLowerCase();
}

export function normalizeExperiment(value: string | null | undefined) {
  return (value ?? "").trim().toLowerCase();
}

export function parseExperimentsFromSummary(summary: string | null): RequestedExperiment[] {
  return parseExperimentSummary(summary).map((item) => ({
    lab_name: item.lab_name,
    experiment_item: item.experiment_item,
  }));
}

export function getRequestedExperiments(sample: Sample | null) {
  const raw = sample?.experiment_item ?? "";

  return raw
    .split("、")
    .map((part) => part.trim())
    .filter(Boolean)
    .map((part) => {
      const { value: experimentPart, route_prefix } = stripExperimentRoutePrefix(part);
      const maybeMeta = route_prefix ?? "G1#1";
      const [rawGroup, rawTarget] = maybeMeta.includes("#") ? maybeMeta.split("#", 2) : ["G1", "1"];

      const separatorIndex = experimentPart.indexOf(":");
      const labName = separatorIndex === -1 ? "" : experimentPart.slice(0, separatorIndex);
      const experimentItem =
        separatorIndex === -1 ? experimentPart : experimentPart.slice(separatorIndex + 1);

      const target = Number(rawTarget);

      return {
        lab_name: labName.trim(),
        experiment_item: experimentItem.trim(),
        targetGroup: rawGroup.trim() || "G1",
        target: Number.isFinite(target) ? target : 1,
      };
    })
    .filter((experiment) => experiment.lab_name && experiment.experiment_item);
}

export function findMatchingWipForExperiment(sampleWips: Wip[], experiment: RequestedExperiment) {
  return (
    sampleWips.find(
      (wip) =>
        normalizeLab(wip.lab_name) === normalizeLab(experiment.lab_name) &&
        normalizeExperiment(wip.experiment_item) === normalizeExperiment(experiment.experiment_item)
    ) ?? null
  );
}

export function isExperimentCompleted(sampleWips: Wip[], experiment: RequestedExperiment) {
  return sampleWips.some(
    (wip) =>
      normalizeLab(wip.lab_name) === normalizeLab(experiment.lab_name) &&
      normalizeExperiment(wip.experiment_item) ===
        normalizeExperiment(experiment.experiment_item) &&
      wip.status === "completed"
  );
}

export function findCompletedTransferBoundaryIndex(
  requestedExperiments: RequestedExperiment[],
  sampleWips: Wip[],
  currentLab: string
) {
  let currentLabCompletedBoundary = -1;

  for (let index = 0; index < requestedExperiments.length; index += 1) {
    const experiment = requestedExperiments[index];

    if (!isExperimentCompleted(sampleWips, experiment)) {
      break;
    }

    if (normalizeLab(experiment.lab_name) === normalizeLab(currentLab)) {
      currentLabCompletedBoundary = index;
    }
  }

  return currentLabCompletedBoundary;
}

export function formatDateTime(value: string | null | undefined) {
  if (!value) return "-";

  try {
    return new Date(value).toLocaleString("zh-TW", {
      hour12: false,
    });
  } catch {
    return value;
  }
}

export function getCandidateKey(candidate: Candidate) {
  if (candidate.kind === "transfer") {
    return `transfer-${candidate.sample.id}-${candidate.nextWip?.id ?? `${candidate.nextLab}-${candidate.nextExperiment.experiment_item}`}`;
  }

  return `return-${candidate.sample.id}`;
}

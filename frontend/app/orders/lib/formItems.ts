import type { Experiment, FormItem, MasterData, SampleFormGroup } from "../types";

export function groupItemsBySample(formItems: FormItem[]): SampleFormGroup[] {
  return formItems.reduce<SampleFormGroup[]>((groups, item, index) => {
    const lastGroup = groups.at(-1);

    if (lastGroup && lastGroup.sampleId === item.sampleId) {
      lastGroup.endIndex = index;
      lastGroup.items.push({ item, index });
      return groups;
    }

    groups.push({
      sampleId: item.sampleId,
      startIndex: index,
      endIndex: index,
      items: [{ item, index }],
    });
    return groups;
  }, []);
}

export function getDefaultExperimentForLab(masterData: Pick<MasterData, "experiments">, labId: string) {
  return masterData.experiments.find((experiment) => experiment.labId === labId)?.id || "";
}

export function generateSampleId(index: number) {
  return `S${String(index).padStart(3, "0")}`;
}

export function getNextSampleId(formItems: FormItem[]) {
  const sampleIds = new Set(formItems.map((item) => item.sampleId).filter(Boolean));
  return generateSampleId(sampleIds.size + 1);
}

export function createDefaultItem(masterData: Pick<MasterData, "labs" | "experiments">, sampleId = generateSampleId(1)): FormItem {
  const firstLab = masterData.labs[0]?.id || "";
  return {
    sampleId,
    labId: firstLab,
    experimentId: firstLab ? getDefaultExperimentForLab(masterData, firstLab) : "",
  };
}

export function toggleExperimentInGroup(
  current: FormItem[],
  group: SampleFormGroup,
  experiment: Experiment,
  checked: boolean
) {
  const existingIndex = current.findIndex(
    (item, index) =>
      index >= group.startIndex &&
      index <= group.endIndex &&
      item.experimentId === experiment.id
  );

  if (checked) {
    if (existingIndex >= 0) return current;

    const next = [...current];
    next.splice(group.endIndex + 1, 0, {
      sampleId: group.sampleId,
      labId: experiment.labId,
      experimentId: experiment.id,
    });
    return next;
  }

  if (existingIndex < 0 || current.length <= 1) return current;
  return current.filter((_, index) => index !== existingIndex);
}

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

export function getDefaultExperimentForLab(
  masterData: Pick<MasterData, "experiments">,
  labId: string
) {
  return masterData.experiments.find((experiment) => experiment.labId === labId)?.id || "";
}

function getTodayText() {
  const now = new Date();

  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");

  return `${year}${month}${day}`;
}

export function generateSampleId(index: number, dateText = getTodayText()) {
  return `SMP-${dateText}-${String(index).padStart(3, "0")}`;
}

function getSampleSequence(sampleId: string, dateText = getTodayText()) {
  const match = sampleId.trim().match(new RegExp(`^SMP-${dateText}-(\\d+)$`, "i"));
  return match ? Number(match[1]) : 0;
}

export function getNextSampleId(formItems: FormItem[]) {
  const dateText = getTodayText();

  const maxSequence = formItems.reduce((max, item) => {
    return Math.max(max, getSampleSequence(item.sampleId, dateText));
  }, 0);

  return generateSampleId(maxSequence + 1, dateText);
}

export function getNextSampleIdFromOrders(orders: { items?: { sampleId?: string }[] }[]) {
  const dateText = getTodayText();

  const maxSequence = orders.reduce((max, order) => {
    const itemMax = (order.items || []).reduce((innerMax, item) => {
      return Math.max(innerMax, getSampleSequence(item.sampleId || "", dateText));
    }, 0);

    return Math.max(max, itemMax);
  }, 0);

  return generateSampleId(maxSequence + 1, dateText);
}

export function createDefaultItem(
  masterData: Pick<MasterData, "labs" | "experiments">,
  sampleId = generateSampleId(1)
): FormItem {
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
      index >= group.startIndex && index <= group.endIndex && item.experimentId === experiment.id
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

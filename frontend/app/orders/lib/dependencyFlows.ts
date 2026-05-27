import type { FormItem } from "../types";

export type IndexedDependencyItem = {
  item: FormItem;
  index: number;
};

export type DependencyFlow = {
  id: string;
  name: string;
  sampleId?: string;
  sampleName?: string;
  items: IndexedDependencyItem[];
};

export type DependencyFlowState = {
  flows: DependencyFlow[];
  independentItems: IndexedDependencyItem[];
};

function normalizeItem(item: FormItem, targetGroup: string, target: number): FormItem {
  return {
    ...item,
    targetGroup,
    target,
    check: false,
  };
}

function targetGroupNumber(targetGroup: string) {
  const match = targetGroup.match(/^G(\d+)$/i);
  return match ? Number(match[1]) : 0;
}

function sortByDependencyTarget(items: IndexedDependencyItem[]) {
  return [...items].sort((left, right) => {
    const leftTarget = left.item.target || 1;
    const rightTarget = right.item.target || 1;
    return leftTarget - rightTarget || left.index - right.index;
  });
}

export function isExperimentItem(item: Pick<FormItem, "labId" | "experimentId">) {
  return Boolean(item.labId.trim() && item.experimentId.trim());
}

export function createNextTargetGroup(existing: (FormItem | string)[]) {
  const maxGroup = existing.reduce((max, item) => {
    const targetGroup = typeof item === "string" ? item : item.targetGroup;
    return Math.max(max, targetGroupNumber(targetGroup));
  }, 0);

  return `G${maxGroup + 1}`;
}

export function buildDependencyFlowsFromItems(
  items: IndexedDependencyItem[],
  explicitFlowIds: string[] = []
): DependencyFlowState {
  const byGroup = new Map<string, IndexedDependencyItem[]>();
  const groupMeta = new Map<string, Pick<FormItem, "sampleId" | "sampleName">>();

  items.forEach((indexedItem) => {
    const targetGroup = indexedItem.item.targetGroup || `G${indexedItem.index + 1}`;
    groupMeta.set(targetGroup, {
      sampleId: indexedItem.item.sampleId,
      sampleName: indexedItem.item.sampleName,
    });

    if (!isExperimentItem(indexedItem.item)) {
      byGroup.set(targetGroup, byGroup.get(targetGroup) || []);
      return;
    }

    byGroup.set(targetGroup, [...(byGroup.get(targetGroup) || []), indexedItem]);
  });

  const groupIds = Array.from(new Set([...Array.from(byGroup.keys()), ...explicitFlowIds])).sort(
    (left, right) => targetGroupNumber(left) - targetGroupNumber(right) || left.localeCompare(right)
  );

  const flows = groupIds.map<DependencyFlow>((groupId, flowIndex) => {
    const groupItems = sortByDependencyTarget(byGroup.get(groupId) || []);

    return {
      id: groupId,
      name: `相依流程 ${flowIndex + 1}`,
      sampleId: groupMeta.get(groupId)?.sampleId,
      sampleName: groupMeta.get(groupId)?.sampleName,
      items: groupItems.map((entry, targetIndex) => ({
        ...entry,
        item: normalizeItem(entry.item, groupId, targetIndex + 1),
      })),
    };
  });

  return { flows, independentItems: [] };
}

export function normalizeTargetsInFlow(flow: DependencyFlow): DependencyFlow {
  return {
    ...flow,
    items: flow.items.map((entry, index) => ({
      ...entry,
      item: normalizeItem(entry.item, flow.id, index + 1),
    })),
  };
}

export function flattenDependencyFlowsToItems(
  flows: DependencyFlow[],
  independentItems: IndexedDependencyItem[] = []
): FormItem[] {
  const flowItems = flows.flatMap((flow) => {
    const normalizedFlow = normalizeTargetsInFlow(flow);
    const experimentItems = normalizedFlow.items
      .filter(({ item }) => isExperimentItem(item))
      .map(({ item }) => item);

    if (experimentItems.length > 0) {
      return experimentItems;
    }

    return [
      {
        sampleId: normalizedFlow.sampleId || "",
        sampleName: normalizedFlow.sampleName || "",
        labId: "",
        experimentId: "",
        targetGroup: normalizedFlow.id,
        target: 1,
        check: false,
      },
    ];
  });

  const independent = independentItems
    .filter(({ item }) => isExperimentItem(item))
    .map(({ item }, index) =>
      normalizeItem(item, createNextTargetGroup([...flows.map((flow) => flow.id), `G${index}`]), 1)
    );

  return [...flowItems, ...independent];
}

export function moveItemInFlow(
  flows: DependencyFlow[],
  flowId: string,
  itemIndex: number,
  direction: -1 | 1
): DependencyFlow[] {
  return flows.map((flow) => {
    if (flow.id !== flowId) return flow;

    const targetIndex = itemIndex + direction;
    if (targetIndex < 0 || targetIndex >= flow.items.length) return flow;

    const nextItems = [...flow.items];
    [nextItems[itemIndex], nextItems[targetIndex]] = [nextItems[targetIndex], nextItems[itemIndex]];

    return normalizeTargetsInFlow({ ...flow, items: nextItems });
  });
}

export function moveItemToFlow(
  state: DependencyFlowState,
  sourceFlowId: string,
  itemIndex: number,
  targetFlowId: string
): DependencyFlowState {
  if (sourceFlowId === targetFlowId) return state;

  const sourceFlow = state.flows.find((flow) => flow.id === sourceFlowId);
  const movedItem = sourceFlow?.items[itemIndex];

  if (!sourceFlow || !movedItem || !state.flows.some((flow) => flow.id === targetFlowId)) {
    return state;
  }

  return {
    ...state,
    flows: state.flows.map((flow) => {
      if (flow.id === sourceFlowId) {
        return normalizeTargetsInFlow({
          ...flow,
          items: flow.items.filter((_, index) => index !== itemIndex),
        });
      }

      if (flow.id === targetFlowId) {
        return normalizeTargetsInFlow({
          ...flow,
          items: [...flow.items, movedItem],
        });
      }

      return flow;
    }),
  };
}

export function removeItemFromFlow(
  state: DependencyFlowState,
  flowId: string,
  itemIndex: number
): DependencyFlowState {
  const flow = state.flows.find((item) => item.id === flowId);
  const removedItem = flow?.items[itemIndex];

  if (!flow || !removedItem) return state;

  const nextFlowId = createNextTargetGroup(state.flows.map((item) => item.id));

  return {
    ...state,
    flows: [
      ...state.flows.map((item) =>
        item.id === flowId
          ? normalizeTargetsInFlow({
              ...item,
              items: item.items.filter((_, index) => index !== itemIndex),
            })
          : item
      ),
      normalizeTargetsInFlow({
        id: nextFlowId,
        name: `相依流程 ${state.flows.length + 1}`,
        items: [
          {
            ...removedItem,
            item: normalizeItem(removedItem.item, nextFlowId, 1),
          },
        ],
      }),
    ],
  };
}

export function normalizeDependencyItemsForSubmit(items: FormItem[]) {
  const normalizedItems: FormItem[] = [];
  let nextGroupNumber = 1;

  const sampleGroups = items.reduce<FormItem[][]>((groups, item) => {
    const lastGroup = groups.at(-1);

    if (lastGroup && lastGroup[0]?.sampleId === item.sampleId) {
      lastGroup.push(item);
      return groups;
    }

    groups.push([item]);
    return groups;
  }, []);

  sampleGroups.forEach((sampleItems) => {
    const state = buildDependencyFlowsFromItems(
      sampleItems.map((item, index) => ({ item, index }))
    );

    state.flows.forEach((flow) => {
      const targetGroup = `G${nextGroupNumber}`;
      nextGroupNumber += 1;
      normalizeTargetsInFlow({ ...flow, id: targetGroup }).items.forEach(({ item }) => {
        normalizedItems.push(item);
      });
    });
  });

  return normalizedItems;
}

export function getEmptyDependencyFlowNames(items: FormItem[]) {
  const emptyFlowNames: string[] = [];

  const sampleGroups = items.reduce<FormItem[][]>((groups, item) => {
    const lastGroup = groups.at(-1);

    if (lastGroup && lastGroup[0]?.sampleId === item.sampleId) {
      lastGroup.push(item);
      return groups;
    }

    groups.push([item]);
    return groups;
  }, []);

  sampleGroups.forEach((sampleItems) => {
    const state = buildDependencyFlowsFromItems(
      sampleItems.map((item, index) => ({ item, index }))
    );

    state.flows.forEach((flow) => {
      if (flow.items.length === 0) {
        emptyFlowNames.push(flow.name);
      }
    });
  });

  return emptyFlowNames;
}

import { useState, type ReactNode } from "react";
import { displayExperimentName, displayLabName } from "@/lib/displayNames";
import {
  buildDependencyFlowsFromItems,
  createNextTargetGroup,
  flattenDependencyFlowsToItems,
  isExperimentItem,
  moveItemInFlow,
  moveItemToFlow,
  removeItemFromFlow,
  normalizeTargetsInFlow,
} from "../lib/dependencyFlows";
import {
  buttonStyle,
  emptyStyle,
  experimentLabGroupStyle,
  inputStyle,
  itemCardStyle,
} from "../styles";
import type { FormItem, MasterData, SampleFormGroup } from "../types";
import { Field } from "./common";

export function SampleExperimentEditor({
  groups,
  items,
  masterData,
  onSampleChange,
  onSampleNameChange,
  onDependencyItemsChange,
}: {
  groups: SampleFormGroup[];
  items: FormItem[];
  masterData: Pick<MasterData, "labs" | "experiments">;
  onSampleChange: (group: SampleFormGroup, sampleId: string) => void;
  onSampleNameChange: (group: SampleFormGroup, sampleName: string) => void;
  onDependencyItemsChange: (group: SampleFormGroup, nextItems: FormItem[]) => void;
}) {
  const [explicitFlowIdsByGroup, setExplicitFlowIdsByGroup] = useState<Record<string, string[]>>(
    {}
  );

  function getGroupKey(group: SampleFormGroup) {
    return `${group.startIndex}-${group.sampleId}`;
  }

  return (
    <div style={{ display: "grid", gap: 12, marginTop: 10 }}>
      {groups.map((group, groupIndex) => {
        const groupKey = getGroupKey(group);
        const explicitFlowIds = explicitFlowIdsByGroup[groupKey] || [];
        const dependencyState = buildDependencyFlowsFromItems(group.items, explicitFlowIds);
        const experimentCount = group.items.filter(({ item }) => isExperimentItem(item)).length;

        function updateDependencyState(nextState: typeof dependencyState) {
          onDependencyItemsChange(
            group,
            flattenDependencyFlowsToItems(nextState.flows, nextState.independentItems)
          );
        }

        function addFlow() {
          const nextFlowId = createNextTargetGroup([
            ...items,
            ...Object.values(explicitFlowIdsByGroup).flat(),
          ]);

          setExplicitFlowIdsByGroup((current) => ({
            ...current,
            [groupKey]: [...(current[groupKey] || []), nextFlowId],
          }));
          updateDependencyState({
            ...dependencyState,
            flows: [
              ...dependencyState.flows,
              {
                id: nextFlowId,
                name: `相依流程 ${dependencyState.flows.length + 1}`,
                sampleId: group.sampleId,
                sampleName: group.sampleName,
                items: [],
              },
            ],
          });
        }

        return (
          <div key={`${group.startIndex}-${group.sampleId}`} style={itemCardStyle}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
              <strong style={{ fontSize: 13 }}>樣品 {groupIndex + 1}</strong>
              <span style={{ color: "var(--text3)", fontSize: 12 }}>
                已選 {experimentCount} 個實驗
              </span>
            </div>

            <Field label="樣品編號">
              <input
                value={group.sampleId}
                onChange={(event) => onSampleChange(group, event.target.value)}
                style={inputStyle}
              />
            </Field>

            <Field label="樣品名稱">
              <input
                value={group.sampleName}
                onChange={(event) => onSampleNameChange(group, event.target.value)}
                placeholder="選填，例如：測試樣品 A"
                style={inputStyle}
              />
            </Field>

            <DependencyFlowEditor
              state={dependencyState}
              group={group}
              masterData={masterData}
              onAddFlow={addFlow}
              onAddExperiment={(flowId, experimentId) => {
                const experiment = masterData.experiments.find((item) => item.id === experimentId);
                if (!experiment) return;

                updateDependencyState({
                  ...dependencyState,
                  flows: dependencyState.flows.map((flow) =>
                    flow.id === flowId
                      ? normalizeTargetsInFlow({
                          ...flow,
                          items: [
                            ...flow.items,
                            {
                              index: group.endIndex + 1,
                              item: {
                                sampleId: group.sampleId,
                                sampleName: group.sampleName,
                                labId: experiment.labId,
                                experimentId: experiment.id,
                                targetGroup: flow.id,
                                target: flow.items.length + 1,
                                check: false,
                              },
                            },
                          ],
                        })
                      : flow
                  ),
                });
              }}
              onMoveItem={(flowId, itemIndex, direction) =>
                updateDependencyState({
                  ...dependencyState,
                  flows: moveItemInFlow(dependencyState.flows, flowId, itemIndex, direction),
                })
              }
              onMoveItemToFlow={(sourceFlowId, itemIndex, targetFlowId) =>
                updateDependencyState(
                  moveItemToFlow(dependencyState, sourceFlowId, itemIndex, targetFlowId)
                )
              }
              onRemoveItem={(flowId, itemIndex) =>
                updateDependencyState(removeItemFromFlow(dependencyState, flowId, itemIndex))
              }
              onDeleteItem={(flowId, itemIndex) =>
                updateDependencyState({
                  ...dependencyState,
                  flows: dependencyState.flows.map((flow) =>
                    flow.id === flowId
                      ? normalizeTargetsInFlow({
                          ...flow,
                          items: flow.items.filter((_, index) => index !== itemIndex),
                        })
                      : flow
                  ),
                })
              }
            />
          </div>
        );
      })}
    </div>
  );
}

function DependencyFlowEditor({
  state,
  group,
  masterData,
  onAddFlow,
  onAddExperiment,
  onMoveItem,
  onMoveItemToFlow,
  onRemoveItem,
  onDeleteItem,
}: {
  state: ReturnType<typeof buildDependencyFlowsFromItems>;
  group: SampleFormGroup;
  masterData: Pick<MasterData, "labs" | "experiments">;
  onAddFlow: () => void;
  onAddExperiment: (flowId: string, experimentId: string) => void;
  onMoveItem: (flowId: string, itemIndex: number, direction: -1 | 1) => void;
  onMoveItemToFlow: (sourceFlowId: string, itemIndex: number, targetFlowId: string) => void;
  onRemoveItem: (flowId: string, itemIndex: number) => void;
  onDeleteItem: (flowId: string, itemIndex: number) => void;
}) {
  const [selectedMoveByItem, setSelectedMoveByItem] = useState<Record<string, string>>({});
  const [selectedExperimentByFlow, setSelectedExperimentByFlow] = useState<Record<string, string>>(
    {}
  );
  const selectedExperimentIds = new Set(
    group.items.filter(({ item }) => isExperimentItem(item)).map(({ item }) => item.experimentId)
  );
  const availableExperiments = masterData.experiments.filter(
    (experiment) => !selectedExperimentIds.has(experiment.id)
  );

  return (
    <div style={{ borderTop: "1px solid var(--border)", marginTop: 14, paddingTop: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <h4 style={{ margin: 0, fontSize: 14 }}>相依流程設定</h4>
          <p style={{ color: "var(--text3)", fontSize: 12, lineHeight: 1.6, margin: "6px 0 0" }}>
            同一個流程中的實驗會依序執行；不同流程可以獨立進行。
          </p>
        </div>
        <button type="button" onClick={onAddFlow} style={buttonStyle("blue")}>
          ＋新增相依流程
        </button>
      </div>

      <div style={{ display: "grid", gap: 10, marginTop: 12 }}>
        {state.flows.map((flow) => (
          <div key={flow.id} style={experimentLabGroupStyle}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: 8,
                flexWrap: "wrap",
              }}
            >
              <div style={{ fontWeight: 800, fontSize: 13 }}>{flow.name}</div>
              <div
                style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}
              >
                <select
                  aria-label="選擇要加入的實驗"
                  value={selectedExperimentByFlow[flow.id] || availableExperiments[0]?.id || ""}
                  onChange={(event) =>
                    setSelectedExperimentByFlow((current) => ({
                      ...current,
                      [flow.id]: event.target.value,
                    }))
                  }
                  style={{ ...inputStyle, width: 220, padding: "7px 8px" }}
                  disabled={availableExperiments.length === 0}
                >
                  {availableExperiments.length === 0 ? (
                    <option value="">沒有可加入的實驗</option>
                  ) : (
                    availableExperiments.map((experiment) => (
                      <option key={experiment.id} value={experiment.id}>
                        {displayLabName(masterData, experiment.labId)} / {experiment.name}
                      </option>
                    ))
                  )}
                </select>
                <button
                  type="button"
                  onClick={() =>
                    onAddExperiment(
                      flow.id,
                      selectedExperimentByFlow[flow.id] || availableExperiments[0]?.id || ""
                    )
                  }
                  disabled={availableExperiments.length === 0}
                  style={buttonStyle("green")}
                >
                  加入實驗
                </button>
              </div>
            </div>
            {flow.items.length === 0 ? (
              <div style={{ ...emptyStyle, marginTop: 8, padding: 12 }}>尚未加入實驗</div>
            ) : (
              <div style={{ display: "grid", gap: 8, marginTop: 8 }}>
                {flow.items.map(({ item }, itemIndex) => (
                  <DependencyItemRow
                    key={`${flow.id}-${item.labId}-${item.experimentId}-${itemIndex}`}
                    item={item}
                    masterData={masterData}
                    prefix={`${itemIndex + 1}.`}
                    actions={
                      <>
                        {state.flows.length > 1 && (
                          <>
                            <select
                              aria-label="選擇要移到的流程"
                              value={
                                selectedMoveByItem[`${flow.id}-${itemIndex}`] ||
                                state.flows.find((candidate) => candidate.id !== flow.id)?.id ||
                                ""
                              }
                              onChange={(event) =>
                                setSelectedMoveByItem((current) => ({
                                  ...current,
                                  [`${flow.id}-${itemIndex}`]: event.target.value,
                                }))
                              }
                              style={{ ...inputStyle, width: 132, padding: "7px 8px" }}
                            >
                              {state.flows
                                .filter((candidate) => candidate.id !== flow.id)
                                .map((candidate) => (
                                  <option key={candidate.id} value={candidate.id}>
                                    {candidate.name}
                                  </option>
                                ))}
                            </select>
                            <button
                              type="button"
                              onClick={() =>
                                onMoveItemToFlow(
                                  flow.id,
                                  itemIndex,
                                  selectedMoveByItem[`${flow.id}-${itemIndex}`] ||
                                    state.flows.find((candidate) => candidate.id !== flow.id)!.id
                                )
                              }
                              style={buttonStyle("green")}
                            >
                              移到流程
                            </button>
                          </>
                        )}
                        <button
                          type="button"
                          onClick={() => onMoveItem(flow.id, itemIndex, -1)}
                          disabled={itemIndex === 0}
                          style={buttonStyle("gray")}
                        >
                          上移
                        </button>
                        <button
                          type="button"
                          onClick={() => onMoveItem(flow.id, itemIndex, 1)}
                          disabled={itemIndex === flow.items.length - 1}
                          style={buttonStyle("gray")}
                        >
                          下移
                        </button>
                        <button
                          type="button"
                          onClick={() => onRemoveItem(flow.id, itemIndex)}
                          style={buttonStyle("red")}
                        >
                          拆成新流程
                        </button>
                        <button
                          type="button"
                          onClick={() => onDeleteItem(flow.id, itemIndex)}
                          style={buttonStyle("red")}
                        >
                          移除實驗
                        </button>
                      </>
                    }
                  />
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function DependencyItemRow({
  item,
  masterData,
  prefix,
  actions,
}: {
  item: FormItem;
  masterData: Pick<MasterData, "labs" | "experiments">;
  prefix: string;
  actions: ReactNode;
}) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "minmax(0, 1fr) auto",
        gap: 8,
        alignItems: "center",
        background: "var(--s2)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: 10,
      }}
    >
      <div style={{ minWidth: 0, fontSize: 12 }}>
        <strong>{prefix}</strong> {displayLabName(masterData, item.labId)} /{" "}
        {displayExperimentName(masterData, item.experimentId)}
      </div>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", justifyContent: "flex-end" }}>
        {actions}
      </div>
    </div>
  );
}

import {
  checkboxRowStyle,
  experimentChecklistStyle,
  experimentHeaderStyle,
  experimentLabGroupStyle,
  itemCardStyle,
  subItemStyle,
} from "../styles";
import type { Experiment, FormItem, MasterData, SampleFormGroup } from "../types";
import { displayExperimentName, displayLabName } from "@/lib/displayNames";
import { Field } from "./common";
import { inputStyle, buttonStyle } from "../styles";

export function SampleExperimentEditor({
  groups,
  items,
  masterData,
  onSampleChange,
  onSampleNameChange,
  onDependencyChange,
  onToggleExperiment,
  onMoveExperiment,
  onRemoveItem,
}: {
  groups: SampleFormGroup[];
  items: FormItem[];
  masterData: Pick<MasterData, "labs" | "experiments">;
  onSampleChange: (group: SampleFormGroup, sampleId: string) => void;
  onSampleNameChange: (group: SampleFormGroup, sampleName: string) => void;
  onDependencyChange: (
    index: number,
    field: "targetGroup" | "target",
    value: string | number
  ) => void;
  onToggleExperiment: (group: SampleFormGroup, experiment: Experiment, checked: boolean) => void;
  onMoveExperiment: (index: number, direction: -1 | 1) => void;
  onRemoveItem: (index: number) => void;
}) {
  return (
    <div style={{ display: "grid", gap: 12, marginTop: 10 }}>
      {groups.map((group, groupIndex) => (
        <div key={`${group.startIndex}-${group.sampleId}`} style={itemCardStyle}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
            <strong style={{ fontSize: 13 }}>樣品 {groupIndex + 1}</strong>
            <span style={{ color: "var(--text3)", fontSize: 12 }}>
              已選 {group.items.length} 項實驗
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
              placeholder="例如：晶圓切片 A"
              style={inputStyle}
            />
          </Field>

          <div style={experimentChecklistStyle}>
            {masterData.labs.map((lab) => {
              const labExperiments = masterData.experiments.filter(
                (experiment) => experiment.labId === lab.id
              );
              if (labExperiments.length === 0) return null;

              return (
                <div key={lab.id} style={experimentLabGroupStyle}>
                  <div style={{ fontWeight: 800, fontSize: 12, color: "var(--text2)" }}>
                    {displayLabName(masterData, lab.id)}
                  </div>
                  <div style={{ display: "grid", gap: 6, marginTop: 6 }}>
                    {labExperiments.map((experiment) => {
                      const checked = group.items.some(
                        ({ item }) => item.experimentId === experiment.id
                      );
                      return (
                        <label key={experiment.id} style={checkboxRowStyle}>
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={(event) =>
                              onToggleExperiment(group, experiment, event.target.checked)
                            }
                          />
                          <span>{experiment.name}</span>
                        </label>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>

          <div style={{ display: "grid", gap: 10, marginTop: 12 }}>
            {group.items.map(({ item, index }, experimentIndex) => {
              const lab = masterData.labs.find((candidate) => candidate.id === item.labId);
              const experiment = masterData.experiments.find(
                (candidate) => candidate.id === item.experimentId
              );
              const canMoveUp = experimentIndex > 0;
              const canMoveDown = experimentIndex < group.items.length - 1;

              return (
                <div key={`${index}-${item.labId}-${item.experimentId}`} style={subItemStyle}>
                  <div style={experimentHeaderStyle}>
                    <div style={{ display: "grid", gap: 3 }}>
                      <strong>實驗 {experimentIndex + 1}</strong>
                      <span style={{ color: "var(--text2)", fontSize: 12 }}>
                        {displayLabName(masterData, lab?.id || item.labId)} /{" "}
                        {displayExperimentName(masterData, experiment?.id || item.experimentId)}
                      </span>
                    </div>
                    <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                      <button
                        type="button"
                        onClick={() => onMoveExperiment(index, -1)}
                        style={buttonStyle("gray")}
                        disabled={!canMoveUp}
                      >
                        上移
                      </button>
                      <button
                        type="button"
                        onClick={() => onMoveExperiment(index, 1)}
                        style={buttonStyle("gray")}
                        disabled={!canMoveDown}
                      >
                        下移
                      </button>
                      {items.length > 1 && (
                        <button
                          type="button"
                          onClick={() => onRemoveItem(index)}
                          style={buttonStyle("red")}
                        >
                          移除
                        </button>
                      )}
                    </div>
                  </div>
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "1fr 120px",
                      gap: 8,
                      marginTop: 8,
                    }}
                  >
                    <label style={{ display: "grid", gap: 4 }}>
                      <span style={{ fontSize: 12, color: "var(--text3)" }}>Target Group</span>
                      <input
                        value={item.targetGroup}
                        onChange={(event) =>
                          onDependencyChange(index, "targetGroup", event.target.value)
                        }
                        placeholder="G1"
                        style={inputStyle}
                      />
                    </label>

                    <label style={{ display: "grid", gap: 4 }}>
                      <span style={{ fontSize: 12, color: "var(--text3)" }}>Target</span>
                      <input
                        type="number"
                        min={1}
                        value={item.target}
                        onChange={(event) =>
                          onDependencyChange(index, "target", Number(event.target.value) || 1)
                        }
                        style={inputStyle}
                      />
                    </label>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

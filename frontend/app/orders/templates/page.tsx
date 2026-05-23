"use client";

import Link from "next/link";
import { useEffect, useState, useRef } from "react";
import type { CSSProperties } from "react";

type Lab = {
  id: string;
  name: string;
};

type Experiment = {
  id: string;
  name: string;
  labId: string;
};

type MasterData = {
  labs: Lab[];
  experiments: Experiment[];
};

type FormItem = {
  sampleId: string;
  labId: string;
  experimentId: string;
};

type OrderTemplate = {
  id: string;
  name: string;
  items: FormItem[];
  createdAt: string;
  updatedAt?: string;
};

type SampleFormGroup = {
  sampleId: string;
  startIndex: number;
  endIndex: number;
  items: { item: FormItem; index: number }[];
};

type ApiResponse<T> = {
  success: boolean;
  data: T;
  message?: string;
};

const apiBase = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const templateStoragePrefix = "order-management-templates";

const defaultMasterData: MasterData = {
  labs: [
    { id: "LAB001", name: "可靠度實驗室" },
    { id: "LAB002", name: "材料分析實驗室" },
    { id: "LAB003", name: "影像分析實驗室" },
  ],
  experiments: [
    { id: "EXP001", name: "溫濕度測試", labId: "LAB001" },
    { id: "EXP002", name: "壽命測試", labId: "LAB001" },
    { id: "EXP003", name: "成分分析", labId: "LAB002" },
    { id: "EXP004", name: "SEM 觀察", labId: "LAB003" },
  ],
};

const emptyItem: FormItem = {
  sampleId: "S001",
  labId: "LAB001",
  experimentId: "EXP001",
};

async function requestJson<T>(path: string): Promise<ApiResponse<T>> {
  const response = await fetch(`${apiBase}${path}`);
  const payload = await response.json();

  if (!response.ok) {
    throw new Error(payload.detail || payload.message || "API request failed");
  }

  return payload as ApiResponse<T>;
}

function templateStorageKey(applicantId: string) {
  return `${templateStoragePrefix}:${applicantId || "anonymous"}`;
}

function groupItemsBySample(formItems: FormItem[]): SampleFormGroup[] {
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

export default function OrderTemplatesPage() {
  const [applicantId, setApplicantId] = useState("user001");
  const [templates, setTemplates] = useState<OrderTemplate[]>([]);
  const [masterData, setMasterData] = useState<MasterData>(defaultMasterData);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [templateName, setTemplateName] = useState("");
  const [items, setItems] = useState<FormItem[]>([{ ...emptyItem }]);
  const [message, setMessage] = useState("選擇既有模板，或建立一個新的樣品實驗模板。");
  const [nameError, setNameError] = useState("");
  const nameInputRef = useRef<HTMLInputElement | null>(null);

  function loadTemplates(userId: string) {
    try {
      const raw = window.localStorage.getItem(templateStorageKey(userId));
      const parsed = raw ? (JSON.parse(raw) as OrderTemplate[]) : [];
      setTemplates(Array.isArray(parsed) ? parsed : []);
    } catch {
      setTemplates([]);
    }
  }

  function persistTemplates(nextTemplates: OrderTemplate[]) {
    setTemplates(nextTemplates);
    window.localStorage.setItem(templateStorageKey(applicantId), JSON.stringify(nextTemplates));
  }

  function resetEditor() {
    setSelectedTemplateId(null);
    setTemplateName("");
    setItems([{ ...emptyItem }]);
    setMessage("已清空編輯區，可以建立新模板。");
  }

  function selectTemplate(template: OrderTemplate) {
    setSelectedTemplateId(template.id);
    setTemplateName(template.name);
    setItems(template.items.map((item) => ({ ...item })));
    setMessage(`正在編輯模板：${template.name}`);
  }

  function defaultExperimentForLab(labId: string) {
    return masterData.experiments.find((experiment) => experiment.labId === labId)?.id || "";
  }

  function defaultItem(sampleId: string): FormItem {
    const firstLab = masterData.labs[0]?.id || "LAB001";
    return {
      sampleId,
      labId: firstLab,
      experimentId: defaultExperimentForLab(firstLab) || "EXP001",
    };
  }

  function saveTemplate() {
    const name = templateName.trim();

    if (!name) {
      setNameError("模板名稱不可為空");
      setMessage("請先輸入模板名稱。");
      // focus the input to guide the user
      if (nameInputRef.current) nameInputRef.current.focus();
      return;
    }

    if (
      items.some((item) => !item.sampleId.trim() || !item.labId.trim() || !item.experimentId.trim())
    ) {
      setMessage("每個樣品與實驗都需要填寫樣品編號、實驗室與實驗項目。");
      return;
    }

    const now = new Date().toISOString();

    if (selectedTemplateId) {
      const nextTemplates = templates.map((template) =>
        template.id === selectedTemplateId
          ? {
              ...template,
              name,
              items: items.map((item) => ({ ...item })),
              updatedAt: now,
            }
          : template
      );
      persistTemplates(nextTemplates);
      setMessage(`已更新模板：${name}`);
      return;
    }

    const nextTemplate: OrderTemplate = {
      id: `${Date.now()}`,
      name,
      items: items.map((item) => ({ ...item })),
      createdAt: now,
      updatedAt: now,
    };

    persistTemplates([nextTemplate, ...templates]);
    setSelectedTemplateId(nextTemplate.id);
    setMessage(`已建立模板：${name}`);
  }

  function deleteTemplate(templateId: string) {
    const template = templates.find((item) => item.id === templateId);
    const nextTemplates = templates.filter((item) => item.id !== templateId);
    persistTemplates(nextTemplates);

    if (selectedTemplateId === templateId) {
      resetEditor();
    }

    setMessage(`已刪除模板：${template?.name || templateId}`);
  }

  function addSample() {
    setItems((current) => [...current, defaultItem(`S${String(Date.now()).slice(-5)}`)]);
  }

  function removeItem(index: number) {
    setItems((current) =>
      current.length <= 1 ? current : current.filter((_, itemIndex) => itemIndex !== index)
    );
  }

  function updateSampleGroup(group: SampleFormGroup, sampleId: string) {
    setItems((current) =>
      current.map((item, index) =>
        index >= group.startIndex && index <= group.endIndex ? { ...item, sampleId } : item
      )
    );
  }

  function moveExperiment(index: number, direction: -1 | 1) {
    setItems((current) => {
      const targetIndex = index + direction;
      const item = current[index];
      const target = current[targetIndex];

      if (!item || !target || item.sampleId !== target.sampleId) return current;

      const next = [...current];
      [next[index], next[targetIndex]] = [next[targetIndex], next[index]];
      return next;
    });
  }

  function toggleExperimentForSample(
    group: SampleFormGroup,
    experiment: Experiment,
    checked: boolean
  ) {
    setItems((current) => {
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
          sampleId: group.sampleId || "S001",
          labId: experiment.labId,
          experimentId: experiment.id,
        });
        return next;
      }

      if (existingIndex < 0 || current.length <= 1) return current;
      return current.filter((_, index) => index !== existingIndex);
    });
  }

  useEffect(() => {
    async function loadMasterData() {
      try {
        const response = await requestJson<MasterData>("/api/master-data");
        setMasterData({
          labs: response.data.labs,
          experiments: response.data.experiments,
        });
      } catch {
        setMasterData(defaultMasterData);
      }
    }

    void loadMasterData();
  }, []);

  useEffect(() => {
    queueMicrotask(() => {
      loadTemplates(applicantId);
      resetEditor();
    });
  }, [applicantId]);

  const sampleGroups = groupItemsBySample(items);

  return (
    <div>
      <div style={pageHeaderStyle}>
        <div>
          <h1 style={pageTitleStyle}>實驗模板管理</h1>
          <p style={pageSubtitleStyle}>依樣品建立模板，並保留每個樣品底下的實驗順序。</p>
        </div>
        <Link href="/orders" style={{ textDecoration: "none" }}>
          <span style={{ ...buttonStyle("gray"), display: "inline-flex", whiteSpace: "nowrap" }}>
            回委託單管理
          </span>
        </Link>
      </div>

      <div style={workspaceStyle}>
        <div style={{ display: "grid", gap: 16, alignContent: "start" }}>
          <Panel title="模板清單">
            <Field label="申請人 applicantId">
              <input
                value={applicantId}
                onChange={(event) => setApplicantId(event.target.value)}
                style={inputStyle}
              />
            </Field>

            <button
              type="button"
              onClick={resetEditor}
              style={{ ...buttonStyle("green"), marginTop: 12 }}
            >
              新增模板
            </button>

            <Field label="既有模板">
              <select
                value={selectedTemplateId || ""}
                onChange={(event) => {
                  const template = templates.find((item) => item.id === event.target.value);
                  if (template) {
                    selectTemplate(template);
                  } else {
                    resetEditor();
                  }
                }}
                style={inputStyle}
              >
                <option value="">新增模板 / 未選擇</option>
                {templates.map((template) => (
                  <option key={template.id} value={template.id}>
                    {template.name}（{template.items.length} 筆實驗）
                  </option>
                ))}
              </select>
            </Field>

            {selectedTemplateId ? (
              <div style={selectedTemplateSummaryStyle}>
                <div style={{ fontWeight: 800 }}>{templateName}</div>
                <div style={{ color: "var(--text3)", fontSize: 12, marginTop: 4 }}>
                  {sampleGroups.length} 個樣品，{items.length} 筆實驗
                </div>
              </div>
            ) : (
              <div style={emptyStyle}>尚未選擇模板。</div>
            )}
          </Panel>

          <Panel title="操作訊息">
            <pre style={logStyle}>{message}</pre>
          </Panel>
        </div>

        <Panel title={selectedTemplateId ? "編輯模板" : "新增模板"}>
          <Field label="模板名稱">
            <input
              ref={nameInputRef}
              value={templateName}
              onChange={(event) => {
                setTemplateName(event.target.value);
                if (nameError) setNameError("");
              }}
              placeholder="例如：可靠度常測 3 項"
              style={inputStyle}
            />
            {nameError && (
              <div style={{ color: "var(--red)", fontSize: 12, marginTop: 6 }}>{nameError}</div>
            )}
          </Field>

          <div style={sectionHeaderStyle}>
            <h3 style={{ margin: 0, fontSize: 14 }}>樣品與實驗順序</h3>
            <button type="button" onClick={addSample} style={buttonStyle("blue")}>
              新增樣品
            </button>
          </div>

          <div style={{ display: "grid", gap: 12, marginTop: 10 }}>
            {sampleGroups.map((group, groupIndex) => (
              <div key={`${group.startIndex}-${group.sampleId}`} style={itemCardStyle}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                  <strong>樣品 {groupIndex + 1}</strong>
                  <span style={{ color: "var(--text2)", fontSize: 12 }}>
                    已選 {group.items.length} 個實驗
                  </span>
                </div>

                <Field label="樣品編號">
                  <input
                    value={group.sampleId}
                    onChange={(event) => updateSampleGroup(group, event.target.value)}
                    style={inputStyle}
                  />
                </Field>

                <div style={experimentChecklistStyle}>
                  {masterData.labs.map((lab) => {
                    const labExperiments = masterData.experiments.filter(
                      (experiment) => experiment.labId === lab.id
                    );

                    if (labExperiments.length === 0) {
                      return null;
                    }

                    return (
                      <div key={lab.id} style={experimentLabGroupStyle}>
                        <div style={{ fontWeight: 800, fontSize: 12, color: "var(--text2)" }}>
                          {lab.name} ({lab.id})
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
                                    toggleExperimentForSample(
                                      group,
                                      experiment,
                                      event.target.checked
                                    )
                                  }
                                />
                                <span>
                                  {experiment.name} ({experiment.id})
                                </span>
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
                              {lab?.name || item.labId} / {experiment?.name || item.experimentId}
                            </span>
                          </div>
                          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                            <button
                              type="button"
                              onClick={() => moveExperiment(index, -1)}
                              style={buttonStyle("gray")}
                              disabled={!canMoveUp}
                            >
                              上移
                            </button>
                            <button
                              type="button"
                              onClick={() => moveExperiment(index, 1)}
                              style={buttonStyle("gray")}
                              disabled={!canMoveDown}
                            >
                              下移
                            </button>
                            {items.length > 1 && (
                              <button
                                type="button"
                                onClick={() => removeItem(index)}
                                style={buttonStyle("red")}
                              >
                                移除
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>

          <div style={footerActionsStyle}>
            {selectedTemplateId && (
              <button
                type="button"
                onClick={() => deleteTemplate(selectedTemplateId)}
                style={buttonStyle("red")}
              >
                刪除模板
              </button>
            )}
            <button type="button" onClick={resetEditor} style={buttonStyle("gray")}>
              清空
            </button>
            <button type="button" onClick={saveTemplate} style={buttonStyle("green")}>
              {selectedTemplateId ? "儲存修改" : "建立模板"}
            </button>
          </div>
        </Panel>
      </div>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section style={panelStyle}>
      <h2 style={panelTitleStyle}>{title}</h2>
      {children}
    </section>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label style={{ display: "block", marginTop: 10 }}>
      <div style={{ fontSize: 12, color: "var(--text3)", marginBottom: 4 }}>{label}</div>
      {children}
    </label>
  );
}

const pageHeaderStyle: CSSProperties = {
  marginBottom: 24,
  display: "flex",
  justifyContent: "space-between",
  gap: 16,
  alignItems: "flex-start",
};

const pageTitleStyle: CSSProperties = {
  fontSize: 22,
  fontWeight: 800,
  margin: 0,
};

const pageSubtitleStyle: CSSProperties = {
  color: "var(--text3)",
  fontSize: 12,
  marginTop: 4,
  fontFamily: "monospace",
};

const workspaceStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "340px 1fr",
  gap: 16,
};

const panelStyle: CSSProperties = {
  background: "var(--s1)",
  border: "1px solid var(--border)",
  borderRadius: 12,
  padding: 16,
  boxShadow: "0 10px 30px rgba(0,0,0,.18)",
};

const panelTitleStyle: CSSProperties = {
  margin: "0 0 12px",
  fontSize: 16,
  fontWeight: 800,
};

const inputStyle: CSSProperties = {
  width: "100%",
  background: "var(--s2)",
  border: "1px solid var(--border)",
  borderRadius: 8,
  color: "var(--text)",
  padding: "9px 10px",
  outline: "none",
};

const sectionHeaderStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  marginTop: 16,
};

const itemCardStyle: CSSProperties = {
  background: "var(--s2)",
  border: "1px solid var(--border2)",
  borderRadius: 10,
  padding: 12,
};

const experimentChecklistStyle: CSSProperties = {
  display: "grid",
  gap: 10,
  marginTop: 12,
};

const experimentLabGroupStyle: CSSProperties = {
  border: "1px solid var(--border)",
  borderRadius: 8,
  padding: 10,
};

const checkboxRowStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 8,
  color: "var(--text2)",
  fontSize: 12,
};

const subItemStyle: CSSProperties = {
  borderTop: "1px solid var(--border)",
  paddingTop: 10,
};

const experimentHeaderStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: 8,
  alignItems: "center",
  flexWrap: "wrap",
};

const emptyStyle: CSSProperties = {
  padding: 18,
  textAlign: "center",
  color: "var(--text3)",
  border: "1px dashed var(--border)",
  borderRadius: 10,
  background: "var(--s2)",
  marginTop: 10,
};

const selectedTemplateSummaryStyle: CSSProperties = {
  background: "var(--s2)",
  border: "1px solid var(--border2)",
  borderRadius: 10,
  marginTop: 10,
  padding: 12,
};

const logStyle: CSSProperties = {
  background: "#05070a",
  border: "1px solid var(--border2)",
  borderRadius: 8,
  padding: 10,
  minHeight: 120,
  maxHeight: 220,
  overflow: "auto",
  color: "#a6e3a1",
  fontSize: 11,
  whiteSpace: "pre-wrap",
};

const footerActionsStyle: CSSProperties = {
  display: "flex",
  justifyContent: "flex-end",
  flexWrap: "wrap",
  gap: 8,
  marginTop: 16,
  // Ensure the footer actions sit above possible overlays and accept pointer events
  position: "relative",
  zIndex: 30,
  pointerEvents: "auto",
};

function buttonStyle(kind: "blue" | "green" | "gray" | "red"): CSSProperties {
  const colors = {
    blue: "var(--blue)",
    green: "var(--green)",
    gray: "var(--s3)",
    red: "var(--red)",
  };

  return {
    background: colors[kind],
    color: kind === "gray" ? "var(--text2)" : "#fff",
    border: "1px solid var(--border)",
    borderRadius: 7,
    padding: "7px 10px",
    cursor: "pointer",
    // Ensure button accepts pointer events even if parent has overlays
    pointerEvents: "auto",
    fontSize: 12,
  };
}

"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/contexts/AuthContext";
import { apiGet, apiPost } from "@/lib/api";
import { getErrorMessage } from "@/lib/error";
import { masterDataApi } from "@/services/master-data-api";
import type { CurrentUser, Sample, Wip, WipForm } from "./types";
import { activeSampleStatuses, wipStatusText, priorityText } from "./constants";
import {
  createEmptyWipForm,
  getCurrentLab,
  getRequestedExperiments,
  makeAutoFormsForSample,
  formatRequestedExperiments,
  shouldOpenCreateWipByDefault,
} from "./utils/wipForm";
import { CollapsibleSection, InfoItem, Field, StatusBadge } from "./components/WipCommon";
import {
  titleStyle,
  headerStyle,
  headerActionsStyle,
  subtitleStyle,
  layoutStyle,
  leftPanelStyle,
  mainPanelStyle,
  panelStyle,
  panelHeaderStyle,
  sectionButtonGroupStyle,
  panelHintStyle,
  countBadgeStyle,
  sampleListStyle,
  sampleCardStyle,
  sampleCardTopStyle,
  sampleNameStyle,
  sampleMetaStyle,
  monoTextStyle,
  detailGridStyle,
  autoGenerateNoticeStyle,
  warningNoticeStyle,
  formListStyle,
  formCardStyle,
  formCardHeaderStyle,
  formActionsStyle,
  formGridStyle,
  inputStyle,
  textareaStyle,
  submitBarStyle,
  labListStyle,
  labGroupStyle,
  labGroupHeaderStyle,
  wipListStyle,
  wipCardStyle,
  wipTitleStyle,
  wipMetaStyle,
  emptyStyle,
  errorStyle,
  successStyle,
  autoTagStyle,
  primaryButtonStyle,
  secondaryButtonStyle,
  smallSecondaryButtonStyle,
  smallDangerButtonStyle,
} from "./styles";

type ApiListResponse<T> = T[] | { data?: T[] };

function normalizeApiArray<T>(payload: ApiListResponse<T>): T[] {
  if (Array.isArray(payload)) return payload;
  return Array.isArray(payload.data) ? payload.data : [];
}

export default function WipPage() {
  const searchParams = useSearchParams();
  const sampleIdFromUrl = searchParams.get("sampleId");
  const { user: authUser } = useAuth();
  const masterQuery = useQuery({
    queryKey: ["master-data"],
    queryFn: masterDataApi.fetch,
  });

  const [samples, setSamples] = useState<Sample[]>([]);
  const [wips, setWips] = useState<Wip[]>([]);
  const [selectedSampleId, setSelectedSampleId] = useState<string>(sampleIdFromUrl ?? "");
  const [forms, setForms] = useState<WipForm[]>([createEmptyWipForm("")]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const [openSections, setOpenSections] = useState({
    sampleInfo: true,
    createWip: true,
    currentWips: true,
  });

  const currentLabData = masterQuery.data?.labs.find((lab) => lab.id === authUser?.labId);
  const currentDepartment = masterQuery.data?.departments.find(
    (department) => department.id === authUser?.departmentId
  );
  const labNameById = useMemo(() => {
    const map = new Map<string, string>();
    masterQuery.data?.labs.forEach((lab) => {
      map.set(lab.id, lab.name);
    });
    return map;
  }, [masterQuery.data?.labs]);

  const currentUser = useMemo<CurrentUser | null>(() => {
    if (!authUser) return null;

    return {
      id: authUser.id,
      name: authUser.name,
      role: authUser.role,
      department: currentDepartment?.name ?? currentDepartment?.code ?? "",
      lab_name: currentLabData?.name ?? null,
      email: authUser.email,
    };
  }, [authUser, currentDepartment, currentLabData]);

  const currentLab = getCurrentLab(currentUser);
  const currentOperatorName = currentUser?.name ?? "";

  const getWipLabName = useCallback(
    (wip: Wip) => {
      if (wip.lab_name) return wip.lab_name;
      if (wip.lab_id) return labNameById.get(wip.lab_id) ?? wip.lab_id;
      return "未指定實驗室";
    },
    [labNameById]
  );

  const activeSamples = useMemo(() => {
    return samples.filter((sample) => activeSampleStatuses.has(sample.status));
  }, [samples]);

  const selectedSample = useMemo(() => {
    return activeSamples.find((sample) => sample.id === selectedSampleId) ?? null;
  }, [activeSamples, selectedSampleId]);

  const requestedExperiments = useMemo(() => {
    return getRequestedExperiments(selectedSample);
  }, [selectedSample]);

  const experimentOptionsByLab = useMemo(() => {
    const map = new Map<string, string[]>();

    function addOption(
      labName: string | null | undefined,
      experimentName: string | null | undefined
    ) {
      if (!labName || !experimentName) return;

      const options = map.get(labName) ?? [];

      if (!options.includes(experimentName)) {
        options.push(experimentName);
      }

      map.set(labName, options);
    }

    masterQuery.data?.experiments.forEach((experiment) => {
      const lab = masterQuery.data?.labs.find((candidate) => candidate.id === experiment.labId);

      addOption(lab?.name, experiment.name);
      addOption(lab?.code, experiment.name);
    });

    requestedExperiments.forEach((experiment) => {
      addOption(experiment.lab_name, experiment.experiment_item);
    });

    return map;
  }, [masterQuery.data?.experiments, masterQuery.data?.labs, requestedExperiments]);

  const currentLabRequestedExperiments = useMemo(() => {
    return requestedExperiments.filter((item) => item.lab_name === currentLab);
  }, [requestedExperiments, currentLab]);

  const selectedWips = useMemo(() => {
    if (!selectedSampleId) return [];

    return wips.filter((wip) => {
      return wip.sample_id === selectedSampleId && getWipLabName(wip) === currentLab;
    });
  }, [wips, selectedSampleId, currentLab, getWipLabName]);

  const wipsByLab = useMemo(() => {
    return selectedWips.reduce<Record<string, Wip[]>>((groups, wip) => {
      const labName = getWipLabName(wip);

      if (!groups[labName]) {
        groups[labName] = [];
      }

      groups[labName].push(wip);
      return groups;
    }, {});
  }, [selectedWips, getWipLabName]);

  const canCreateWip =
    selectedSample?.status === "received" ||
    selectedSample?.status === "split" ||
    selectedSample?.status === "pending_transfer";

  const hasAutoGeneratedForms = forms.some((form) => form.auto_generated);

  function getExperimentOptionsForLab(labName: string) {
    return experimentOptionsByLab.get(labName) ?? [];
  }

  function toggleSection(section: keyof typeof openSections) {
    setOpenSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }));
  }

  function resetFormsForSample(sample: Sample | null, lab: string, wipData: Wip[]) {
    setForms(makeAutoFormsForSample(sample, lab, wipData));

    setOpenSections((prev) => ({
      ...prev,
      sampleInfo: true,
      createWip: shouldOpenCreateWipByDefault(sample),
      currentWips: true,
    }));
  }

  async function loadData() {
    if (!currentUser) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError("");
      setSuccessMessage("");

      const [samplePayload, wipPayload] = await Promise.all([
        apiGet<ApiListResponse<Sample>>("/api/samples"),
        apiGet<ApiListResponse<Wip>>("/api/wips"),
      ]);

      const sampleData = normalizeApiArray(samplePayload);
      const wipData = normalizeApiArray(wipPayload);
      const lab = getCurrentLab(currentUser);

      setSamples(sampleData);
      setWips(wipData);

      const activeSampleData = sampleData.filter((sample) =>
        activeSampleStatuses.has(sample.status)
      );

      // 如果網址有帶 sampleId，就只在「真的找得到且可操作」時自動選它。
      // 找不到或不可操作時，不要跳紅色錯誤，避免沒資料時畫面看起來像壞掉。
      if (sampleIdFromUrl) {
        const target = sampleData.find((sample) => sample.id === sampleIdFromUrl);

        if (target && activeSampleStatuses.has(target.status)) {
          setSelectedSampleId(target.id);
          resetFormsForSample(target, lab, wipData);
          return;
        }

        const firstTargetSample =
          activeSampleData.find((sample) => sample.status === "received") ?? activeSampleData[0];

        if (firstTargetSample) {
          setSelectedSampleId(firstTargetSample.id);
          resetFormsForSample(firstTargetSample, lab, wipData);
          return;
        }

        setSelectedSampleId("");
        setForms([createEmptyWipForm(lab)]);
        setOpenSections({
          sampleInfo: true,
          createWip: true,
          currentWips: true,
        });

        return;
      }

      const currentSelected = activeSampleData.find((sample) => sample.id === selectedSampleId);

      if (currentSelected) {
        resetFormsForSample(currentSelected, lab, wipData);
        return;
      }

      const firstTargetSample =
        activeSampleData.find((sample) => sample.status === "received") ?? activeSampleData[0];

      if (firstTargetSample) {
        setSelectedSampleId(firstTargetSample.id);
        resetFormsForSample(firstTargetSample, lab, wipData);
      } else {
        setSelectedSampleId("");
        setForms([createEmptyWipForm(lab)]);
        setOpenSections({
          sampleInfo: true,
          createWip: true,
          currentWips: true,
        });
      }
    } catch (err) {
      setError(getErrorMessage(err, "載入資料失敗"));
    } finally {
      setLoading(false);
    }
  }

  function handleSelectSample(sampleId: string) {
    const targetSample = activeSamples.find((sample) => sample.id === sampleId) ?? null;

    setSelectedSampleId(sampleId);
    resetFormsForSample(targetSample, currentLab, wips);
    setError("");
    setSuccessMessage("");
  }

  function updateForm(index: number, field: keyof WipForm, value: string | boolean) {
    setForms((prev) => {
      return prev.map((form, formIndex) => {
        if (formIndex !== index) return form;

        return {
          ...form,
          [field]: value,
          auto_generated: field === "experiment_item" ? false : form.auto_generated,
        };
      });
    });
  }

  function addForm() {
    setForms((prev) => [...prev, createEmptyWipForm(currentLab)]);

    setOpenSections((prev) => ({
      ...prev,
      createWip: true,
    }));
  }

  function regenerateFormsFromOrder() {
    if (!selectedSample) return;

    setForms(makeAutoFormsForSample(selectedSample, currentLab, wips));
    setOpenSections((prev) => ({
      ...prev,
      createWip: true,
    }));
    setSuccessMessage("已重新依照委託單實驗需求產生 WIP 項目");
  }

  function duplicateForm(index: number) {
    setForms((prev) => {
      const target = prev[index];
      if (!target) return prev;

      return [
        ...prev.slice(0, index + 1),
        {
          ...target,
          experiment_item: "",
          note: "",
          auto_generated: false,
        },
        ...prev.slice(index + 1),
      ];
    });

    setOpenSections((prev) => ({
      ...prev,
      createWip: true,
    }));
  }

  function removeForm(index: number) {
    setForms((prev) => {
      if (prev.length === 1) return prev;
      return prev.filter((_, formIndex) => formIndex !== index);
    });
  }

  function validateForms() {
    if (!selectedSample) {
      return "請先選擇樣品";
    }

    if (!canCreateWip) {
      return "目前樣品狀態不可分貨，需為「已收樣」或「已分貨」";
    }

    for (let index = 0; index < forms.length; index += 1) {
      const form = forms[index];

      if (!form.experiment_item.trim()) {
        return `第 ${index + 1} 筆 WIP 尚未填寫實驗項目`;
      }

      if (!form.priority.trim()) {
        return `第 ${index + 1} 筆 WIP 尚未選擇優先級`;
      }

      if (!form.lab_name.trim()) {
        return `第 ${index + 1} 筆 WIP 尚未指定實驗室`;
      }
    }

    const duplicated = new Set<string>();

    for (const form of forms) {
      const key = `${form.lab_name}::${form.experiment_item}`;

      if (duplicated.has(key)) {
        return `WIP 項目重複：${form.lab_name} / ${form.experiment_item}`;
      }

      duplicated.add(key);
    }

    return "";
  }

  async function submitSplit() {
    try {
      setSubmitting(true);
      setError("");
      setSuccessMessage("");

      const validationMessage = validateForms();

      if (validationMessage) {
        setError(validationMessage);
        return;
      }

      if (!selectedSample) {
        setError("找不到指定樣品");
        return;
      }

      await apiPost(`/api/samples/${selectedSample.id}/actions`, {
        action: "split",
        operator_name: currentOperatorName,
        wips: forms.map((form) => ({
          lab_name: form.lab_name || currentLab,
          experiment_item: form.experiment_item,
          priority: form.priority,
          // 不送 wip_no。
          // WIP 編號統一由後端 generate_unique_wip_no() 產生，
          // 格式固定為 WIP-YYYY-NNNN-{LabCode}-XX。
          //
          // 不送 current_location。
          // 後端會用 sample.current_location，避免 Lab B 的 WIP 在交接前被 Lab B 看到。
          note: form.note,
        })),
      });

      setSuccessMessage("WIP / 實驗子單建立成功");
      setOpenSections({
        sampleInfo: true,
        createWip: false,
        currentWips: true,
      });

      await loadData();
    } catch (err) {
      setError(getErrorMessage(err, "建立 WIP 失敗"));
    } finally {
      setSubmitting(false);
    }
  }

  function goBackToSamplePage() {
    window.location.href = "/sample";
  }

  async function goToSchedulePage() {
    // 先用 B 自己的 send_to_schedule 把本 Lab、此樣品中尚在 created 的 WIP 送入待派工，
    // 讓它們出現在 C 派工頁的「待派工 WIP」挑單清單；再導去派工頁。
    try {
      setSubmitting(true);
      const toSchedule = selectedWips.filter((wip) => wip.status === "created");
      for (const wip of toSchedule) {
        await apiPost(`/api/wips/${wip.id}/actions`, {
          action: "send_to_schedule",
          operator_name: currentOperatorName,
        });
      }
    } catch (err) {
      setError(getErrorMessage(err, "送入待派工失敗"));
      setSubmitting(false);
      return;
    }
    window.location.href = "/dispatch";
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentUser?.id, currentUser?.lab_name]);

  if (!currentUser) {
    return (
      <section style={panelStyle}>
        <div style={emptyStyle}>尚未取得登入身分</div>
      </section>
    );
  }

  return (
    <div>
      <div style={headerStyle}>
        <div>
          <h1 style={titleStyle}>WIP / 分貨管理</h1>
          <p style={subtitleStyle}>WIP MANAGEMENT · 依委託單實驗需求自動產生 WIP 項目</p>
        </div>

        <div style={headerActionsStyle}>
          <button onClick={goBackToSamplePage} style={secondaryButtonStyle}>
            回樣品追蹤
          </button>
          <button onClick={loadData} style={secondaryButtonStyle}>
            重新整理
          </button>
        </div>
      </div>

      {error && <div style={errorStyle}>{error}</div>}
      {successMessage && <div style={successStyle}>{successMessage}</div>}

      {loading ? (
        <section style={panelStyle}>
          <div style={emptyStyle}>載入中...</div>
        </section>
      ) : (
        <div style={layoutStyle}>
          <section style={leftPanelStyle}>
            <div style={panelHeaderStyle}>
              <div>
                <div style={{ fontWeight: 800 }}>可分貨樣品</div>
                <div style={panelHintStyle}>只顯示已收樣或已分貨、可建立 WIP 的樣品</div>
              </div>

              <span style={countBadgeStyle}>{activeSamples.length} 筆</span>
            </div>

            <div style={sampleListStyle}>
              {activeSamples.map((sample) => {
                const active = sample.id === selectedSampleId;
                const sampleRequestedExperiments = getRequestedExperiments(sample);
                const currentLabCount = sampleRequestedExperiments.filter(
                  (item) => item.lab_name === currentLab
                ).length;

                return (
                  <button
                    key={sample.id}
                    onClick={() => handleSelectSample(sample.id)}
                    style={{
                      ...sampleCardStyle,
                      borderColor: active ? "rgba(56,139,253,0.75)" : "var(--border2)",
                      background: active ? "rgba(56,139,253,0.1)" : "var(--s1)",
                    }}
                  >
                    <div style={sampleCardTopStyle}>
                      <span style={monoTextStyle}>{sample.sample_no}</span>
                      <StatusBadge status={sample.status} />
                    </div>

                    <div style={sampleNameStyle}>{sample.sample_name ?? "未命名樣品"}</div>

                    <div style={sampleMetaStyle}>
                      {sample.order_no} ·{" "}
                      {currentLabCount > 0
                        ? `${currentLabCount} 個本 Lab 實驗需求`
                        : "本 Lab 無未建立需求"}
                    </div>

                    <div style={sampleMetaStyle}>位置：{sample.current_location ?? "-"}</div>
                  </button>
                );
              })}

              {activeSamples.length === 0 && <div style={emptyStyle}>目前沒有可分貨的樣品</div>}
            </div>
          </section>

          <main style={mainPanelStyle}>
            {!selectedSample ? (
              <section style={panelStyle}>
                <div style={emptyStyle}>請先選擇一筆可分貨樣品</div>
              </section>
            ) : (
              <>
                <CollapsibleSection
                  title="樣品資訊"
                  hint="目前選擇的樣品與委託單資料"
                  open={openSections.sampleInfo}
                  onToggle={() => toggleSection("sampleInfo")}
                  right={<StatusBadge status={selectedSample.status} />}
                >
                  <div style={detailGridStyle}>
                    <InfoItem label="樣品編號" value={selectedSample.sample_no} />
                    <InfoItem label="委託單號" value={selectedSample.order_no} />
                    <InfoItem label="樣品名稱" value={selectedSample.sample_name ?? "-"} />
                    <InfoItem
                      label="全部實驗需求"
                      value={formatRequestedExperiments(selectedSample)}
                    />
                    <InfoItem label="本 Lab" value={currentLab} />
                    <InfoItem
                      label="本 Lab 實驗需求"
                      value={
                        currentLabRequestedExperiments.length > 0
                          ? currentLabRequestedExperiments
                              .map((item) => item.experiment_item)
                              .join("、")
                          : "無"
                      }
                    />
                    <InfoItem label="申請人" value={selectedSample.applicant_name ?? "-"} />
                    <InfoItem label="申請部門" value={selectedSample.applicant_department ?? "-"} />
                    <InfoItem label="目前位置" value={selectedSample.current_location ?? "-"} />
                    <InfoItem label="備註" value={selectedSample.note ?? "-"} />
                  </div>
                </CollapsibleSection>

                <CollapsibleSection
                  title="建立 WIP / 實驗子單"
                  hint={
                    selectedSample.status === "split"
                      ? "此樣品已分貨，因此此區塊預設收合；若需要補建 WIP 可以展開"
                      : "系統會依照委託單實驗需求預先產生 WIP；必要時仍可新增或修改"
                  }
                  open={openSections.createWip}
                  onToggle={() => toggleSection("createWip")}
                  right={
                    <div style={sectionButtonGroupStyle}>
                      <button
                        onClick={(event) => {
                          event.stopPropagation();
                          regenerateFormsFromOrder();
                        }}
                        style={secondaryButtonStyle}
                        type="button"
                      >
                        重新依單產生
                      </button>

                      <button
                        onClick={(event) => {
                          event.stopPropagation();
                          addForm();
                        }}
                        style={secondaryButtonStyle}
                        type="button"
                      >
                        新增一筆
                      </button>
                    </div>
                  }
                >
                  {hasAutoGeneratedForms && (
                    <div style={autoGenerateNoticeStyle}>
                      已根據委託單實驗需求自動產生 WIP 項目，你可以直接確認建立。
                    </div>
                  )}

                  {!hasAutoGeneratedForms && currentLabRequestedExperiments.length === 0 && (
                    <div style={warningNoticeStyle}>
                      這張單子目前沒有指定 {currentLab} 的實驗需求。若確定要在本 Lab 建立
                      WIP，可以手動新增。
                    </div>
                  )}

                  <div style={formListStyle}>
                    {forms.map((form, index) => (
                      <div
                        key={`${index}-${form.priority}-${form.experiment_item}`}
                        style={formCardStyle}
                      >
                        <div style={formCardHeaderStyle}>
                          <div>
                            <div style={{ fontWeight: 800 }}>
                              WIP #{index + 1}
                              {form.auto_generated && <span style={autoTagStyle}>自動帶入</span>}
                            </div>
                          </div>

                          <div style={formActionsStyle}>
                            <button
                              onClick={() => duplicateForm(index)}
                              type="button"
                              style={smallSecondaryButtonStyle}
                            >
                              複製
                            </button>

                            <button
                              onClick={() => removeForm(index)}
                              type="button"
                              disabled={forms.length === 1}
                              style={{
                                ...smallDangerButtonStyle,
                                opacity: forms.length === 1 ? 0.45 : 1,
                                cursor: forms.length === 1 ? "not-allowed" : "pointer",
                              }}
                            >
                              刪除
                            </button>
                          </div>
                        </div>

                        <div style={formGridStyle}>
                          <Field label="負責實驗室">
                            <input
                              value={form.lab_name}
                              readOnly
                              style={{
                                ...inputStyle,
                                opacity: 0.75,
                                cursor: "not-allowed",
                              }}
                            />
                          </Field>

                          <Field label="實驗項目">
                            <input
                              value={form.experiment_item}
                              onChange={(event) =>
                                updateForm(index, "experiment_item", event.target.value)
                              }
                              list={`experiment-options-${index}`}
                              placeholder="請選擇或輸入實驗項目"
                              style={inputStyle}
                            />

                            <datalist id={`experiment-options-${index}`}>
                              {getExperimentOptionsForLab(form.lab_name).map((item) => (
                                <option key={item} value={item} />
                              ))}
                            </datalist>
                          </Field>

                          <Field label="優先級">
                            <select
                              value={form.priority}
                              onChange={(event) =>
                                updateForm(index, "priority", event.target.value)
                              }
                              style={inputStyle}
                            >
                              <option value="low">低</option>
                              <option value="normal">一般</option>
                              <option value="high">高</option>
                              <option value="urgent">急件</option>
                            </select>
                          </Field>
                        </div>

                        <Field label="備註">
                          <textarea
                            value={form.note}
                            onChange={(event) => updateForm(index, "note", event.target.value)}
                            placeholder="可填寫特殊需求、檢測條件或注意事項"
                            style={textareaStyle}
                          />
                        </Field>
                      </div>
                    ))}
                  </div>

                  <div style={submitBarStyle}>
                    <button
                      onClick={submitSplit}
                      disabled={submitting || !canCreateWip}
                      style={{
                        ...primaryButtonStyle,
                        opacity: submitting || !canCreateWip ? 0.55 : 1,
                        cursor: submitting || !canCreateWip ? "not-allowed" : "pointer",
                      }}
                    >
                      {submitting ? "建立中..." : "建立 WIP / 完成分貨"}
                    </button>
                  </div>
                </CollapsibleSection>

                <CollapsibleSection
                  title="目前已建立的 WIP"
                  hint="只顯示目前實驗室的 WIP / 實驗子單"
                  open={openSections.currentWips}
                  onToggle={() => toggleSection("currentWips")}
                  right={<span style={countBadgeStyle}>{selectedWips.length} 筆</span>}
                >
                  {selectedWips.length === 0 ? (
                    <div style={emptyStyle}>此樣品目前尚未建立本實驗室的 WIP</div>
                  ) : (
                    <div style={labListStyle}>
                      {Object.entries(wipsByLab).map(([labName, labWips]) => (
                        <div key={labName} style={labGroupStyle}>
                          <div style={labGroupHeaderStyle}>
                            <span>{labName}</span>
                            <span style={countBadgeStyle}>{labWips.length} 個實驗</span>
                          </div>

                          <div style={wipListStyle}>
                            {labWips.map((wip) => (
                              <div key={wip.id} style={wipCardStyle}>
                                <div>
                                  <div style={wipTitleStyle}>
                                    {wip.experiment_item ?? "未命名實驗"}
                                  </div>

                                  <div style={wipMetaStyle}>
                                    {wip.wip_no} · 優先級：
                                    {priorityText[wip.priority] ?? wip.priority}
                                  </div>

                                  <div style={wipMetaStyle}>
                                    位置：{wip.current_location ?? "-"}
                                  </div>
                                </div>

                                <div style={{ textAlign: "right" }}>
                                  <div style={{ fontSize: 12, fontWeight: 800 }}>
                                    {wipStatusText[wip.status] ?? wip.status}
                                  </div>

                                  <div style={wipMetaStyle}>進度 {wip.progress}%</div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {selectedWips.length > 0 && (
                    <div style={submitBarStyle}>
                      <button onClick={goToSchedulePage} style={primaryButtonStyle}>
                        前往排程 / 派工
                      </button>
                    </div>
                  )}
                </CollapsibleSection>
              </>
            )}
          </main>
        </div>
      )}
    </div>
  );
}

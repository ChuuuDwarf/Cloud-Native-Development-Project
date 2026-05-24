import { priorityLabel } from "../constants";
import {
  buttonStyle,
  editNoticeStyle,
  inputStyle,
  quotaBoxStyle,
  sectionHeaderStyle,
  templateBoxStyle,
} from "../styles";
import type {
  Experiment,
  FormItem,
  MasterData,
  OrderTemplate,
  PriorityLevel,
  QuotaCheck,
  SampleFormGroup,
  UserNameLookup,
} from "../types";
import { displayScopeName } from "@/lib/displayNames";
import { Field, Input } from "./common";
import { SampleExperimentEditor } from "./SampleExperimentEditor";

export function OrderForm({
  currentUserName,
  currentUser,
  usersById,
  departmentId,
  setDepartmentId,
  priority,
  setPriority,
  masterData,
  quotaCheck,
  templates,
  selectedTemplateId,
  templateName,
  setTemplateName,
  items,
  sampleGroups,
  editingOrderId,
  editingOrderNo,
  submitting,
  onCheckQuota,
  onSaveTemplate,
  onApplyTemplate,
  onAddSample,
  onSampleChange,
  onToggleExperiment,
  onMoveExperiment,
  onRemoveItem,
  onClose,
  onCreate,
  onUpdate,
}: {
  currentUserName: string;
  currentUser: { id: string; name: string };
  usersById: UserNameLookup;
  departmentId: string;
  setDepartmentId: (value: string) => void;
  priority: PriorityLevel;
  setPriority: (value: PriorityLevel) => void;
  masterData: MasterData;
  quotaCheck: QuotaCheck | null;
  templates: OrderTemplate[];
  selectedTemplateId: string;
  templateName: string;
  setTemplateName: (value: string) => void;
  items: FormItem[];
  sampleGroups: SampleFormGroup[];
  editingOrderId: number | null;
  editingOrderNo: string | null;
  submitting: boolean;
  onCheckQuota: () => void;
  onSaveTemplate: () => void;
  onApplyTemplate: (templateId: string) => void;
  onAddSample: () => void;
  onSampleChange: (group: SampleFormGroup, sampleId: string) => void;
  onToggleExperiment: (group: SampleFormGroup, experiment: Experiment, checked: boolean) => void;
  onMoveExperiment: (index: number, direction: -1 | 1) => void;
  onRemoveItem: (index: number) => void;
  onClose: () => void;
  onCreate: (submitAfterCreate: boolean) => void;
  onUpdate: () => void;
}) {
  return (
    <>
      {editingOrderId && (
        <div style={editNoticeStyle}>正在修改委託單 {editingOrderNo}，修改後可以重新送出簽核。</div>
      )}

      <Field label="申請人">
        <Input value={currentUserName || "目前使用者"} onChange={() => {}} disabled />
      </Field>

      <Field label="部門 / 廠區">
        <select
          value={departmentId}
          onChange={(event) => setDepartmentId(event.target.value)}
          style={inputStyle}
        >
          {masterData.departments.map((department) => (
            <option key={department.id} value={department.id}>
              {department.name}
            </option>
          ))}
        </select>
      </Field>

      <Field label="優先程度">
        <select
          value={priority}
          onChange={(event) => setPriority(event.target.value as PriorityLevel)}
          style={inputStyle}
        >
          {Object.entries(priorityLabel).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </Field>

      <div style={{ marginTop: 12 }}>
        <button type="button" onClick={onCheckQuota} style={buttonStyle("blue")}>
          檢查配額
        </button>
      </div>

      {quotaCheck && (
        <div style={quotaBoxStyle}>
          <div style={{ fontWeight: 800, marginBottom: 8 }}>
            {quotaCheck.needOverride ? "配額檢查：超額，需主管特批" : "配額檢查：可送出"}
          </div>
          {quotaCheck.checks.map((check) => (
            <div
              key={`${check.scopeType}-${check.scopeId}`}
              style={{ fontSize: 12, color: "var(--text2)", marginTop: 4 }}
            >
              {check.scopeType === "user"
                ? "個人"
                : check.scopeType === "department"
                  ? "部門"
                  : check.scopeType}{" "}
              /{" "}
              {displayScopeName(masterData, usersById, check.scopeType, check.scopeId, currentUser)}
              ：已用 {check.used} / 上限 {check.limit}，本次 {check.requested}
            </div>
          ))}
        </div>
      )}

      <div style={templateBoxStyle}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: 12,
            alignItems: "center",
          }}
        >
          <div>
            <div style={{ fontWeight: 800 }}>常用實驗模板</div>
            <div style={{ color: "var(--text3)", fontSize: 12, marginTop: 4 }}>
              可將目前明細儲存為模板，之後快速套用。
            </div>
          </div>
          <span style={{ color: "var(--text3)", fontSize: 12 }}>{templates.length} 個模板</span>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 8, marginTop: 12 }}>
          <input
            value={templateName}
            onChange={(event) => setTemplateName(event.target.value)}
            placeholder="輸入模板名稱，例如：可靠度常測 3 項"
            style={inputStyle}
          />
          <button type="button" onClick={onSaveTemplate} style={buttonStyle("green")}>
            儲存模板
          </button>
        </div>

        {templates.length > 0 && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 8, marginTop: 10 }}>
            <select
              value={selectedTemplateId}
              onChange={(event) => onApplyTemplate(event.target.value)}
              style={inputStyle}
            >
              <option value="">選擇模板套用</option>
              {templates.map((template) => (
                <option key={template.id} value={template.id}>
                  {template.name}（{template.items.length} 筆）
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => selectedTemplateId && onApplyTemplate(selectedTemplateId)}
              style={buttonStyle("blue")}
              disabled={!selectedTemplateId}
            >
              套用
            </button>
          </div>
        )}
      </div>

      <div style={sectionHeaderStyle}>
        <h3 style={{ margin: 0, fontSize: 14 }}>樣品與實驗順序</h3>
        <button type="button" onClick={onAddSample} style={buttonStyle("blue")}>
          新增樣品
        </button>
      </div>

      <SampleExperimentEditor
        groups={sampleGroups}
        items={items}
        masterData={masterData}
        onSampleChange={onSampleChange}
        onToggleExperiment={onToggleExperiment}
        onMoveExperiment={onMoveExperiment}
        onRemoveItem={onRemoveItem}
      />

      {editingOrderId ? (
        <button
          type="button"
          onClick={onUpdate}
          style={{ ...buttonStyle("green"), width: "100%", marginTop: 14 }}
        >
          儲存修改
        </button>
      ) : (
        <>
          <button
            type="button"
            onClick={onClose}
            style={{ ...buttonStyle("gray"), width: "100%", marginTop: 14 }}
          >
            取消離開
          </button>
          <button
            type="button"
            onClick={() => onCreate(false)}
            disabled={submitting}
            style={{ ...buttonStyle("green"), width: "100%", marginTop: 8 }}
          >
            {submitting ? "處理中..." : "建立草稿"}
          </button>
          <button
            type="button"
            onClick={() => onCreate(true)}
            disabled={submitting}
            style={{ ...buttonStyle("blue"), width: "100%", marginTop: 8 }}
          >
            {submitting ? "處理中..." : "直接送出"}
          </button>
        </>
      )}
    </>
  );
}

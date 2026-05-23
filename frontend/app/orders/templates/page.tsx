"use client";

import Link from "next/link";
import { Field, Panel } from "../components/common";
import { SampleExperimentEditor } from "../components/SampleExperimentEditor";
import { buttonStyle, emptyStyle, footerActionsStyle, inputStyle, logStyle, pageHeaderStyle, pageSubtitleStyle, pageTitleStyle, sectionHeaderStyle, selectedTemplateSummaryStyle, workspaceStyle } from "../styles";
import { useOrderTemplatesPage } from "./useOrderTemplatesPage";

export default function OrderTemplatesPage() {
  const page = useOrderTemplatesPage();

  return (
    <div>
      <div style={pageHeaderStyle}>
        <div>
          <h1 style={pageTitleStyle}>實驗模板管理</h1>
          <p style={pageSubtitleStyle}>依樣品建立模板，並保留每個樣品底下的實驗順序。</p>
        </div>
        <Link href="/orders" style={{ textDecoration: "none" }}>
          <span style={{ ...buttonStyle("gray"), display: "inline-flex", whiteSpace: "nowrap" }}>回委託單管理</span>
        </Link>
      </div>

      <div style={workspaceStyle}>
        <div style={{ display: "grid", gap: 16, alignContent: "start" }}>
          <Panel title="模板清單">
            <Field label="申請人">
              <input value={page.currentUserName || "目前使用者"} readOnly disabled style={inputStyle} />
            </Field>

            <button type="button" onClick={page.resetEditor} style={{ ...buttonStyle("green"), marginTop: 12 }}>新增模板</button>

            <Field label="既有模板">
              <select
                value={page.selectedTemplateId || ""}
                onChange={(event) => {
                  const template = page.templates.find((item) => item.id === event.target.value);
                  if (template) page.selectTemplate(template);
                  else page.resetEditor();
                }}
                style={inputStyle}
              >
                <option value="">新增模板 / 未選擇</option>
                {page.templates.map((template) => (
                  <option key={template.id} value={template.id}>{template.name}（{template.items.length} 筆實驗）</option>
                ))}
              </select>
            </Field>

            {page.selectedTemplateId ? (
              <div style={selectedTemplateSummaryStyle}>
                <div style={{ fontWeight: 800 }}>{page.templateName}</div>
                <div style={{ color: "var(--text3)", fontSize: 12, marginTop: 4 }}>{page.sampleGroups.length} 個樣品，{page.items.length} 筆實驗</div>
              </div>
            ) : (
              <div style={emptyStyle}>尚未選擇模板。</div>
            )}
          </Panel>

          <Panel title="操作訊息">
            <pre style={logStyle}>{page.message}</pre>
          </Panel>
        </div>

        <Panel title={page.selectedTemplateId ? "編輯模板" : "新增模板"}>
          <Field label="模板名稱">
            <input
              ref={page.nameInputRef}
              value={page.templateName}
              onChange={(event) => {
                page.setTemplateName(event.target.value);
                if (page.nameError) page.setNameError("");
              }}
              placeholder="例如：可靠度常測 3 項"
              style={inputStyle}
            />
            {page.nameError && <div style={{ color: "var(--red)", fontSize: 12, marginTop: 6 }}>{page.nameError}</div>}
          </Field>

          <div style={sectionHeaderStyle}>
            <h3 style={{ margin: 0, fontSize: 14 }}>樣品與實驗順序</h3>
            <button type="button" onClick={page.addSample} style={buttonStyle("blue")}>新增樣品</button>
          </div>

          <SampleExperimentEditor
            groups={page.sampleGroups}
            items={page.items}
            masterData={page.masterData}
            onSampleChange={page.updateSampleGroup}
            onToggleExperiment={page.toggleExperimentForSample}
            onMoveExperiment={page.moveExperiment}
            onRemoveItem={page.removeItem}
          />

          <div style={footerActionsStyle}>
            {page.selectedTemplateId && <button type="button" onClick={() => page.deleteTemplate(page.selectedTemplateId!)} style={buttonStyle("red")}>刪除模板</button>}
            <button type="button" onClick={page.resetEditor} style={buttonStyle("gray")}>清空</button>
            <button type="button" onClick={page.saveTemplate} style={buttonStyle("green")}>{page.selectedTemplateId ? "儲存修改" : "建立模板"}</button>
          </div>
        </Panel>
      </div>
    </div>
  );
}

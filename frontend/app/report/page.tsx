"use client";
import Panel from "@/components/ui/Panel";
import Btn from "@/components/ui/Btn";
import { OfflineBanner } from "@/components/ui/DataState";
import { useReportPage } from "./hooks/useReportPage";
import Banner from "./components/Banner";
import ReportTable from "./components/ReportTable";
import CreateModal from "./components/CreateModal";
import EditModal from "./components/EditModal";
import ReportDetailModal from "./components/ReportDetailModal";
import { pageHeaderStyle, pageTitleStyle, pageSubtitleStyle } from "./styles";

export default function ReportPage() {
  const {
    loading,
    offline,
    templates,
    canStaff,
    isChief,
    creatable,
    draftReports,
    formalReports,
    msg,
    detail,
    setDetail,
    editing,
    setEditing,
    creating,
    setCreating,
    run,
    saveAsTemplate,
    openCreate,
    openEdit,
  } = useReportPage();

  return (
    <div>
      <div style={pageHeaderStyle}>
        <div>
          <h1 style={pageTitleStyle}>實驗報告管理</h1>
          <p style={pageSubtitleStyle}>REPORT · 草稿 → 待審核 → 已確認 → 已發布 → 已回傳</p>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <Btn variant="primary" disabled={offline || !canStaff} onClick={openCreate}>
            ＋ 新增報告
          </Btn>
        </div>
      </div>

      {offline && <OfflineBanner />}
      {msg && <Banner msg={msg} />}

      <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
        <Panel title="草稿 / 審核中" tag={`${draftReports.length} 筆`}>
          <ReportTable
            rows={draftReports}
            loading={loading}
            emptyText="目前沒有草稿。點右上「＋新增報告」從已完成的實驗建立。"
            canStaff={canStaff}
            isChief={isChief}
            offline={offline}
            onEdit={openEdit}
            onDetail={setDetail}
            run={run}
          />
        </Panel>
        <Panel title="正式報告（已確認 / 已發布 / 已回傳）" tag={`${formalReports.length} 筆`}>
          <ReportTable
            rows={formalReports}
            loading={loading}
            emptyText="目前沒有正式報告。"
            canStaff={canStaff}
            isChief={isChief}
            offline={offline}
            onEdit={openEdit}
            onDetail={setDetail}
            run={run}
          />
        </Panel>
      </div>

      {detail && (
        <ReportDetailModal
          r={detail}
          onClose={() => setDetail(null)}
          onSaveTemplate={saveAsTemplate}
        />
      )}
      {editing && <EditModal r={editing} run={run} onClose={() => setEditing(null)} />}
      {creating && (
        <CreateModal
          wips={creatable}
          templates={templates}
          run={run}
          onClose={() => setCreating(false)}
        />
      )}
    </div>
  );
}

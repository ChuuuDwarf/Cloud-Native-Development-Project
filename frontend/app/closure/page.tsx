"use client";
import Panel from "@/components/ui/Panel";
import DataState, { OfflineBanner } from "@/components/ui/DataState";
import { useClosurePage } from "./hooks/useClosurePage";
import Banner from "./components/Banner";
import ClosureTable from "./components/ClosureTable";
import ClosureConditionsModal from "./components/ClosureConditionsModal";
import { pageHeaderStyle, pageTitleStyle, pageSubtitleStyle } from "./styles";

export default function ClosurePage() {
  const { rows, loading, offline, canOperate, msg, detail, setDetail, run } = useClosurePage();

  return (
    <div>
      <div style={pageHeaderStyle}>
        <div>
          <h1 style={pageTitleStyle}>結單管理</h1>
          <p style={pageSubtitleStyle}>CLOSURE · 結單條件檢核 → 轉待取件</p>
        </div>
      </div>

      {offline && <OfflineBanner />}
      {msg && <Banner msg={msg} />}

      <Panel title="委託單結單狀態" tag={`${rows.length} 筆`}>
        <DataState loading={loading} empty={rows.length === 0}>
          <ClosureTable
            rows={rows}
            canOperate={canOperate}
            offline={offline}
            onDetail={setDetail}
            run={run}
          />
        </DataState>
      </Panel>

      {detail && <ClosureConditionsModal detail={detail} onClose={() => setDetail(null)} />}
    </div>
  );
}

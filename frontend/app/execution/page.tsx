"use client";
import Panel from "@/components/ui/Panel";
import DataState, { OfflineBanner } from "@/components/ui/DataState";
import { useExecutionPage } from "./hooks/useExecutionPage";
import Banner from "./components/Banner";
import ExecutionKpis from "./components/ExecutionKpis";
import ExecutionTable from "./components/ExecutionTable";
import ExecutionModalHost from "./components/ExecutionModalHost";
import { pageHeaderStyle, pageTitleStyle, pageSubtitleStyle } from "./styles";

export default function ExecutionPage() {
  const {
    wips,
    loading,
    offline,
    kpi,
    canOperate,
    isChief,
    modal,
    target,
    machines,
    recipes,
    msg,
    run,
    open,
    closeModal,
    flashError,
  } = useExecutionPage();

  return (
    <div>
      <div style={pageHeaderStyle}>
        <div>
          <h1 style={pageTitleStyle}>實驗執行</h1>
          <p style={pageSubtitleStyle}>EXPERIMENT EXECUTION · 上下機 / 進度 / 結果 / 中止</p>
        </div>
      </div>

      {offline && <OfflineBanner />}
      {msg && <Banner msg={msg} />}

      <ExecutionKpis kpi={kpi} />

      <Panel title="實驗執行清單" tag={`${wips.length} 筆`}>
        <DataState loading={loading} empty={wips.length === 0}>
          <ExecutionTable
            wips={wips}
            canOperate={canOperate}
            isChief={isChief}
            offline={offline}
            open={open}
            run={run}
            flashError={flashError}
          />
        </DataState>
      </Panel>

      <ExecutionModalHost
        modal={modal}
        target={target}
        machines={machines}
        recipes={recipes}
        run={run}
        onClose={closeModal}
      />
    </div>
  );
}

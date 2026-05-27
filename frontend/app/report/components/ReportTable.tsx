"use client";
import Chip from "@/components/ui/Chip";
import Btn from "@/components/ui/Btn";
import DataState from "@/components/ui/DataState";
import { reportsApi } from "@/services/reports-api";
import { chipOf } from "@/types/lab";
import type { Report, RunFn } from "../types";
import { TABLE_HEADERS, DRAFT_STATUSES } from "../constants";
import { th, td, tdMono, linkBtn } from "../styles";

function RowActions({
  r,
  canStaff,
  isChief,
  offline,
  onEdit,
  onDetail,
  run,
}: {
  r: Report;
  canStaff: boolean;
  isChief: boolean;
  offline: boolean;
  onEdit: (r: Report) => void;
  onDetail: (r: Report) => void;
  run: RunFn;
}) {
  const d = offline;
  if (DRAFT_STATUSES.includes(r.status) && canStaff) {
    return (
      <>
        <Btn small disabled={d} onClick={() => onEdit(r)}>
          編輯
        </Btn>
        <Btn
          small
          variant="primary"
          disabled={d}
          onClick={() => run(() => reportsApi.submit(r.reportId), "已提交審核")}
        >
          送審
        </Btn>
      </>
    );
  }
  if (r.status === "待審核" && isChief) {
    return (
      <>
        <Btn
          small
          disabled={d}
          onClick={() => run(() => reportsApi.review(r.reportId, { approve: false }), "報告已退回")}
        >
          退回
        </Btn>
        <Btn
          small
          variant="primary"
          disabled={d}
          onClick={() => run(() => reportsApi.review(r.reportId, { approve: true }), "報告已確認")}
        >
          確認
        </Btn>
      </>
    );
  }
  if (r.status === "已確認" && canStaff) {
    return (
      <Btn
        small
        variant="primary"
        disabled={d}
        onClick={() => run(() => reportsApi.publish(r.reportId), "報告已發布並回傳")}
      >
        發布回傳
      </Btn>
    );
  }
  if (r.status === "已發布" || r.status === "已回傳") {
    return (
      <Btn small onClick={() => onDetail(r)}>
        查閱 / 下載
      </Btn>
    );
  }
  return <span style={{ fontSize: 10, color: "var(--text3)" }}>—</span>;
}

export default function ReportTable({
  rows,
  loading,
  emptyText,
  canStaff,
  isChief,
  offline,
  onEdit,
  onDetail,
  run,
}: {
  rows: Report[];
  loading: boolean;
  emptyText: string;
  canStaff: boolean;
  isChief: boolean;
  offline: boolean;
  onEdit: (r: Report) => void;
  onDetail: (r: Report) => void;
  run: RunFn;
}) {
  return (
    <DataState loading={loading} empty={rows.length === 0} emptyText={emptyText}>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "var(--s2)" }}>
              {TABLE_HEADERS.map((h) => (
                <th key={h} style={th}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.reportId} style={{ borderBottom: "1px solid rgba(56,139,253,0.05)" }}>
                <td style={tdMono}>
                  <button onClick={() => onDetail(r)} style={linkBtn}>
                    {r.reportId}
                  </button>
                </td>
                <td style={tdMono}>{r.orderId}</td>
                <td style={td}>{r.title}</td>
                <td style={tdMono}>v{r.versions.length}</td>
                <td style={td}>
                  <Chip type={chipOf(r.status)} label={r.status} />
                </td>
                <td style={td}>
                  <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                    <RowActions
                      r={r}
                      canStaff={canStaff}
                      isChief={isChief}
                      offline={offline}
                      onEdit={onEdit}
                      onDetail={onDetail}
                      run={run}
                    />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </DataState>
  );
}

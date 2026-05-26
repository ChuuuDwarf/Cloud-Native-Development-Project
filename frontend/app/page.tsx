"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import KpiCard from "@/components/ui/KpiCard";
import Chip from "@/components/ui/Chip";
import { formatLab } from "@/components/labDisplay";
import { dashboardApi } from "@/services/dashboard-api";
import LabsPanel from "./_dashboard/LabsPanel";
import DispatchPanel from "./_dashboard/DispatchPanel";
import MachineStatusPanel from "./_dashboard/MachineStatusPanel";
import AttentionPanel from "./_dashboard/AttentionPanel";

const BLOCKED_STATUSES = ["故障中", "保養中", "停用"];

export default function Dashboard() {
  const dashboardQuery = useQuery({
    queryKey: ["dashboard"],
    queryFn: dashboardApi.fetch,
  });
  const dashboard = dashboardQuery.data;

  const isGlobalView = dashboard?.scope === "all";
  const blockedMachines = useMemo(
    () => dashboard?.machines?.filter((machine) => BLOCKED_STATUSES.includes(machine.status)) ?? [],
    [dashboard]
  );

  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: 24,
        }}
      >
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800, letterSpacing: -0.5 }}>主管儀表板</h1>
          <p style={{ fontSize: 12, color: "var(--text3)", marginTop: 4, fontFamily: "monospace" }}>
            SUPERVISOR DASHBOARD · 即時更新
          </p>
        </div>
      </div>

      {/* 通知 Banner */}
      <div
        style={{
          background: "linear-gradient(90deg,rgba(247,129,102,0.1),rgba(247,129,102,0.03))",
          border: "1px solid rgba(247,129,102,0.25)",
          borderRadius: 10,
          padding: "10px 16px",
          display: "flex",
          alignItems: "center",
          gap: 10,
          marginBottom: 20,
          fontSize: 12.5,
        }}
      >
        ⚠️{" "}
        <span>
          <strong style={{ color: "var(--orange)" }}>3 筆委託</strong>即將超過 SLA 時限｜
          <strong style={{ color: "var(--orange)" }}>SEM-001</strong> 機台溫度異常｜
          <strong style={{ color: "var(--orange)" }}>5 筆告警</strong>待處理
        </span>
      </div>

      {/* KPI 卡片 */}
      <div
        style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14, marginBottom: 22 }}
      >
        <KpiCard label="待簽核委託" value={7} sub="今日新增 3 筆" color="var(--blue)" icon="📋" />
        <KpiCard label="實驗室在製量" value={62} sub="↑ 8 較昨日" color="var(--cyan)" icon="🔬" />
        <KpiCard label="逾期 / 告警" value={8} sub="需立即處理" color="var(--red)" icon="🚨" />
        <KpiCard label="今日完成" value={24} sub="自動結單率 78%" color="var(--green)" icon="✅" />
      </div>

      {/* 主內容：左右兩欄 */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 360px", gap: 16 }}>
        {/* 左欄 */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* 待簽核表格 */}
          <div
            style={{
              background: "var(--s1)",
              border: "1px solid var(--border2)",
              borderRadius: 12,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                padding: "14px 18px",
                borderBottom: "1px solid var(--border2)",
                gap: 10,
              }}
            >
              <span style={{ fontWeight: 700, flex: 1 }}>待我簽核</span>
              <span
                style={{
                  fontSize: 10,
                  fontFamily: "monospace",
                  color: "var(--text3)",
                  background: "var(--s3)",
                  padding: "2px 7px",
                  borderRadius: 4,
                }}
              >
                7 筆
              </span>
            </div>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ background: "var(--s2)" }}>
                  {["委託單號", "申請人", "實驗項目", "優先", "送出時間", "操作"].map((h) => (
                    <th
                      key={h}
                      style={{
                        fontSize: 10,
                        letterSpacing: 1.5,
                        color: "var(--text3)",
                        padding: "10px 16px",
                        textAlign: "left",
                        fontFamily: "monospace",
                        borderBottom: "1px solid var(--border2)",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[
                  {
                    id: "WO-2024-0891",
                    name: "王建國 / F12廠",
                    item: "IC 電性測試",
                    prio: "特急",
                    prioCls: "#ff4444",
                    time: "1小時前",
                  },
                  {
                    id: "WO-2024-0892",
                    name: "李美珍 / F6廠",
                    item: "光學量測",
                    prio: "高",
                    prioCls: "#e3b341",
                    time: "3小時前",
                  },
                  {
                    id: "WO-2024-0894",
                    name: "林小玲 / F8廠",
                    item: "熱阻分析",
                    prio: "高",
                    prioCls: "#e3b341",
                    time: "5小時前",
                  },
                  {
                    id: "WO-2024-0897",
                    name: "陳大偉 / F12廠",
                    item: "材料成份分析",
                    prio: "一般",
                    prioCls: "#3d4a56",
                    time: "昨天",
                  },
                ].map((row, i) => (
                  <tr key={i} style={{ borderBottom: "1px solid rgba(56,139,253,0.05)" }}>
                    <td
                      style={{
                        padding: "11px 16px",
                        fontFamily: "monospace",
                        fontSize: 11.5,
                        color: "var(--text2)",
                      }}
                    >
                      {row.id}
                    </td>
                    <td style={{ padding: "11px 16px", fontSize: 12.5 }}>{row.name}</td>
                    <td style={{ padding: "11px 16px", fontSize: 12.5 }}>{row.item}</td>
                    <td style={{ padding: "11px 16px" }}>
                      <span style={{ color: row.prioCls, fontSize: 11, fontFamily: "monospace" }}>
                        ● {row.prio}
                      </span>
                    </td>
                    <td
                      style={{
                        padding: "11px 16px",
                        fontSize: 12.5,
                        color: "var(--text3)",
                        fontFamily: "monospace",
                      }}
                    >
                      {row.time}
                    </td>
                    <td style={{ padding: "11px 16px" }}>
                      <button
                        style={{
                          background: i === 0 ? "var(--blue)" : "var(--s2)",
                          border: "1px solid var(--border)",
                          color: i === 0 ? "#fff" : "var(--text2)",
                          padding: "4px 10px",
                          borderRadius: 6,
                          fontSize: 11,
                          cursor: "pointer",
                        }}
                      >
                        審核
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* WIP 進度 */}
          <div
            style={{
              background: "var(--s1)",
              border: "1px solid var(--border2)",
              borderRadius: 12,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                padding: "14px 18px",
                borderBottom: "1px solid var(--border2)",
                gap: 10,
              }}
            >
              <span style={{ fontWeight: 700, flex: 1 }}>WIP 進度追蹤</span>
              <span
                style={{
                  fontSize: 10,
                  fontFamily: "monospace",
                  color: "var(--text3)",
                  background: "var(--s3)",
                  padding: "2px 7px",
                  borderRadius: 4,
                }}
              >
                前 5 筆
              </span>
            </div>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ background: "var(--s2)" }}>
                  {["WIP 編號", "委託", "機台", "狀態", "進度", "預計完成"].map((h) => (
                    <th
                      key={h}
                      style={{
                        fontSize: 10,
                        letterSpacing: 1.5,
                        color: "var(--text3)",
                        padding: "10px 16px",
                        textAlign: "left",
                        fontFamily: "monospace",
                        borderBottom: "1px solid var(--border2)",
                      }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[
                  {
                    wip: "WIP-0891-01",
                    wo: "WO-0891",
                    machine: "TEM-001",
                    chipType: "running" as const,
                    chipLabel: "執行中",
                    pct: 72,
                    color: "var(--blue)",
                    eta: "18:00",
                  },
                  {
                    wip: "WIP-0891-02",
                    wo: "WO-0891",
                    machine: "XRD-002",
                    chipType: "running" as const,
                    chipLabel: "執行中",
                    pct: 45,
                    color: "var(--blue)",
                    eta: "21:00",
                  },
                  {
                    wip: "WIP-0892-01",
                    wo: "WO-0892",
                    machine: "OPT-001",
                    chipType: "pending" as const,
                    chipLabel: "待上機",
                    pct: 0,
                    color: "var(--blue)",
                    eta: "明日",
                  },
                  {
                    wip: "WIP-0896-01",
                    wo: "WO-0896",
                    machine: "XRD-002",
                    chipType: "done" as const,
                    chipLabel: "已完成",
                    pct: 100,
                    color: "var(--green)",
                    eta: "完成",
                  },
                ].map((row, i) => (
                  <tr key={i} style={{ borderBottom: "1px solid rgba(56,139,253,0.05)" }}>
                    <td
                      style={{
                        padding: "11px 16px",
                        fontFamily: "monospace",
                        fontSize: 11.5,
                        color: "var(--text2)",
                      }}
                    >
                      {row.wip}
                    </td>
                    <td
                      style={{
                        padding: "11px 16px",
                        fontFamily: "monospace",
                        fontSize: 11.5,
                        color: "var(--text2)",
                      }}
                    >
                      {row.wo}
                    </td>
                    <td style={{ padding: "11px 16px", fontSize: 12.5 }}>{row.machine}</td>
                    <td style={{ padding: "11px 16px" }}>
                      <Chip type={row.chipType} label={row.chipLabel} />
                    </td>
                    <td style={{ padding: "11px 16px" }}>
                      <div
                        style={{
                          background: "var(--s3)",
                          borderRadius: 3,
                          height: 5,
                          minWidth: 80,
                        }}
                      >
                        <div
                          style={{
                            width: `${row.pct}%`,
                            height: "100%",
                            borderRadius: 3,
                            background: `linear-gradient(90deg, ${row.color}, var(--cyan))`,
                          }}
                        />
                      </div>
                    </td>
                    <td
                      style={{
                        padding: "11px 16px",
                        fontFamily: "monospace",
                        fontSize: 11.5,
                        color: "var(--text3)",
                      }}
                    >
                      {row.eta}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* 機台使用率 */}
          <div
            style={{
              background: "var(--s1)",
              border: "1px solid var(--border2)",
              borderRadius: 12,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                padding: "14px 18px",
                borderBottom: "1px solid var(--border2)",
                fontWeight: 700,
              }}
            >
              機台使用率{" "}
              <span
                style={{
                  fontSize: 10,
                  fontFamily: "monospace",
                  color: "var(--text3)",
                  background: "var(--s3)",
                  padding: "2px 7px",
                  borderRadius: 4,
                  marginLeft: 8,
                }}
              >
                今日
              </span>
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(3,1fr)",
                gap: 14,
                padding: 16,
              }}
            >
              {[
                { val: "87%", label: "TEM-001 稼動率", color: "var(--cyan)" },
                { val: "93%", label: "XRD-002 稼動率", color: "var(--green)" },
                { val: "停機", label: "AFM-003 狀態", color: "var(--red)" },
              ].map((g, i) => (
                <div
                  key={i}
                  style={{
                    textAlign: "center",
                    background: "var(--s2)",
                    border: "1px solid var(--border2)",
                    borderRadius: 10,
                    padding: 16,
                  }}
                >
                  <div style={{ fontSize: 28, fontWeight: 800, color: g.color, marginBottom: 4 }}>
                    {g.val}
                  </div>
                  <div style={{ fontSize: 10, color: "var(--text3)", fontFamily: "monospace" }}>
                    {g.label}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* 告警通知 */}
          <div
            style={{
              background: "var(--s1)",
              border: "1px solid var(--border2)",
              borderRadius: 12,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                padding: "14px 18px",
                borderBottom: "1px solid var(--border2)",
                gap: 10,
              }}
            >
              <span style={{ fontWeight: 700, flex: 1 }}>告警通知</span>
              <span
                style={{
                  fontSize: 10,
                  fontFamily: "monospace",
                  color: "var(--text3)",
                  background: "var(--s3)",
                  padding: "2px 7px",
                  borderRadius: 4,
                }}
              >
                5 未處理
              </span>
            </div>
            {[
              {
                dot: "var(--red)",
                text: "SEM-001 溫度超標 (+8°C)",
                meta: "3分鐘前 · 機台異常 · 責任人：陳明德",
                glow: true,
              },
              {
                dot: "var(--red)",
                text: "WO-0895 數據異常，需人工審核",
                meta: "12分鐘前 · 數據異常 · 升級中",
              },
              {
                dot: "var(--yellow)",
                text: "3 筆委託即將超過 SLA 時限",
                meta: "28分鐘前 · SLA 告警",
              },
              { dot: "var(--yellow)", text: "試劑庫存低於安全水位", meta: "1小時前 · 倉儲告警" },
              { dot: "var(--blue)", text: "WO-0893 已自動結案", meta: "2小時前 · 系統通知" },
            ].map((a, i) => (
              <div
                key={i}
                style={{
                  display: "flex",
                  gap: 12,
                  padding: "12px 18px",
                  borderBottom: i < 4 ? "1px solid var(--border2)" : "none",
                }}
              >
                <div
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    background: a.dot,
                    flexShrink: 0,
                    marginTop: 5,
                    boxShadow: a.glow ? `0 0 8px ${a.dot}` : "none",
                  }}
                />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 12.5 }}>{a.text}</div>
                  <div
                    style={{
                      fontSize: 10,
                      color: "var(--text3)",
                      fontFamily: "monospace",
                      marginTop: 3,
                    }}
                  >
                    {a.meta}
                  </div>
                </div>
                <button
                  style={{
                    background: "none",
                    border: "1px solid var(--border)",
                    color: "var(--text3)",
                    fontSize: 10,
                    padding: "3px 8px",
                    borderRadius: 5,
                    cursor: "pointer",
                    whiteSpace: "nowrap",
                    fontFamily: "monospace",
                    alignSelf: "flex-start",
                    marginTop: 2,
                  }}
                >
                  處理
                </button>
              </div>
            ))}
          </div>

          {/* 配額狀態 */}
          <div
            style={{
              background: "var(--s1)",
              border: "1px solid var(--border2)",
              borderRadius: 12,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                padding: "14px 18px",
                borderBottom: "1px solid var(--border2)",
                fontWeight: 700,
              }}
            >
              送測配額狀態{" "}
              <span
                style={{
                  fontSize: 10,
                  fontFamily: "monospace",
                  color: "var(--text3)",
                  background: "var(--s3)",
                  padding: "2px 7px",
                  borderRadius: 4,
                  marginLeft: 8,
                }}
              >
                本週
              </span>
            </div>
            <div style={{ padding: 16 }}>
              {[
                { label: "F12廠 部門配額", val: "38/50", pct: 76, type: "ok" },
                { label: "F6廠 部門配額", val: "47/50", pct: 94, type: "warn" },
                { label: "特急單額度", val: "5/5", pct: 100, type: "over" },
                { label: "王建國 個人配額", val: "12/15", pct: 80, type: "ok" },
              ].map((q, i) => (
                <div key={i} style={{ marginBottom: 14 }}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      fontSize: 11,
                      marginBottom: 5,
                    }}
                  >
                    <span style={{ color: "var(--text2)" }}>{q.label}</span>
                    <span style={{ fontFamily: "monospace", color: "var(--text3)" }}>{q.val}</span>
                  </div>
                  <div
                    style={{
                      height: 6,
                      background: "var(--s3)",
                      borderRadius: 3,
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        width: `${q.pct}%`,
                        height: "100%",
                        borderRadius: 3,
                        background:
                          q.type === "ok"
                            ? "linear-gradient(90deg,var(--blue),var(--cyan))"
                            : q.type === "warn"
                              ? "linear-gradient(90deg,var(--yellow),var(--orange))"
                              : "var(--red)",
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 快捷操作 */}
          <div
            style={{
              background: "var(--s1)",
              border: "1px solid var(--border2)",
              borderRadius: 12,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                padding: "14px 18px",
                borderBottom: "1px solid var(--border2)",
                fontWeight: 700,
              }}
            >
              快捷操作
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(3,1fr)",
                gap: 10,
                padding: 14,
              }}
            >
              {[
                { icon: "✅", label: "批次簽核", sub: "7筆待審" },
                { icon: "🗂️", label: "派工排程", sub: "14筆待派" },
                { icon: "⚠️", label: "中止審核", sub: "2筆待判" },
              ].map((a, i) => (
                <div
                  key={i}
                  style={{
                    background: "var(--s2)",
                    border: "1px solid var(--border2)",
                    borderRadius: 10,
                    padding: 16,
                    textAlign: "center",
                    cursor: "pointer",
                  }}
                >
                  <div style={{ fontSize: 24, marginBottom: 8 }}>{a.icon}</div>
                  <div style={{ fontSize: 12, color: "var(--text2)" }}>{a.label}</div>
                  <div
                    style={{
                      fontSize: 10,
                      color: "var(--text3)",
                      marginTop: 3,
                      fontFamily: "monospace",
                    }}
                  >
                    {a.sub}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function statusLine(query: { isLoading: boolean; isError: boolean }): string {
  if (query.isLoading) return "讀取資料庫中";
  if (query.isError) return "後端或 PostgreSQL 尚未啟動";
  return "已連線 PostgreSQL";
}

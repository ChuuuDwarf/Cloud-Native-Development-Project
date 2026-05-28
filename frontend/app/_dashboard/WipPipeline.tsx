"use client";

import type { WipPipeline as WipPipelineData, Pair } from "@/types/dashboard";

const STAGES: Array<{
  key: keyof WipPipelineData;
  label: string;
  color: string;
  drillTo: string;
  pattern?: string;
}> = [
  {
    key: "waiting_dispatch",
    label: "待排程",
    color: "var(--text3)",
    drillTo: "/dispatch",
  },
  { key: "dispatched", label: "排程", color: "var(--cyan)", drillTo: "/dispatch" },
  { key: "in_progress", label: "進行", color: "var(--blue)", drillTo: "/execution" },
  { key: "awaiting_handoff", label: "待傳", color: "var(--orange)", drillTo: "/execution" },
  { key: "done", label: "完", color: "#3fb950", drillTo: "/storage" },
  {
    key: "terminated",
    label: "終止",
    color: "var(--red)",
    drillTo: "/orders?status=terminated",
    pattern: "repeating-linear-gradient(45deg, transparent 0 4px, rgba(0,0,0,0.4) 4px 6px)",
  },
];

function Arrow({ delta }: { delta: number }) {
  if (delta > 0) return <span style={{ color: "#3fb950" }}>↑{delta}</span>;
  if (delta < 0) return <span style={{ color: "var(--red)" }}>↓{Math.abs(delta)}</span>;
  return <span style={{ color: "var(--text3)" }}>→</span>;
}

export default function WipPipeline({ data }: { data: WipPipelineData }) {
  const total = data.total;
  return (
    <div
      data-testid="wip-pipeline"
      style={{
        background: "var(--s1)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: 16,
        height: "100%",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginBottom: 12,
        }}
      >
        <h3 style={{ margin: 0, fontSize: 14 }}>WIP pipeline</h3>
        <span
          style={{
            fontSize: 11,
            color: "var(--text3)",
            fontFamily: "monospace",
          }}
        >
          共 {total} 件
        </span>
      </div>

      {total === 0 ? (
        <div
          style={{
            background: "var(--s2)",
            borderRadius: 4,
            color: "var(--text3)",
            fontSize: 12,
            textAlign: "center",
            padding: 24,
          }}
        >
          目前無 WIP
        </div>
      ) : (
        <>
          <div style={{ display: "flex", height: 14, borderRadius: 4, overflow: "hidden" }}>
            {STAGES.map(({ key, color, pattern }) => {
              const [count] = data[key] as Pair;
              const pct = total > 0 ? (count / total) * 100 : 0;
              if (pct === 0) return null;
              return (
                <div
                  key={key}
                  style={{
                    width: `${pct}%`,
                    background: color,
                    backgroundImage: pattern,
                  }}
                />
              );
            })}
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(6, 1fr)",
              gap: 6,
              marginTop: 14,
              fontSize: 11,
            }}
          >
            {STAGES.map(({ key, label, color, drillTo }) => {
              const [count, delta] = data[key] as Pair;
              return (
                <button
                  key={key}
                  onClick={() => {
                    window.location.href = drillTo;
                  }}
                  style={{
                    background: "transparent",
                    border: "none",
                    color: "var(--text2)",
                    cursor: "pointer",
                    textAlign: "left",
                    padding: 0,
                  }}
                >
                  <div style={{ display: "flex", gap: 4, alignItems: "baseline" }}>
                    <span style={{ color, fontWeight: 600 }}>{label}</span>
                    <span style={{ color: "var(--text1)", fontFamily: "monospace" }}>{count}</span>
                  </div>
                  <div style={{ fontSize: 10, fontFamily: "monospace" }}>
                    <Arrow delta={delta} />
                  </div>
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}

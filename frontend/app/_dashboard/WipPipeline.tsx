"use client";

import { useState } from "react";

import type { WipPipeline as WipPipelineData, Pair } from "@/types/dashboard";

const STAGES: Array<{
  key: keyof Omit<WipPipelineData, "total">;
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
    pattern: "repeating-linear-gradient(45deg, var(--red) 0 4px, transparent 4px 6px)",
  },
];

const BAR_HEIGHT = 40;

function Arrow({ delta }: { delta: number }) {
  if (delta > 0) return <span style={{ color: "#3fb950" }}>↑{delta}</span>;
  if (delta < 0) return <span style={{ color: "var(--red)" }}>↓{Math.abs(delta)}</span>;
  return <span style={{ color: "var(--text3)" }}>→</span>;
}

interface HoverState {
  stageKey: string;
  label: string;
  count: number;
  pct: number;
  delta: number;
  x: number;
  y: number;
}

export default function WipPipeline({ data }: { data: WipPipelineData }) {
  const total = data.total;
  const [hover, setHover] = useState<HoverState | null>(null);

  // Cumulative percent up to (but not including) each stage, used to place
  // the 完工 baseline marker at the right edge of the 完 segment.
  let cumulative = 0;
  const stagePcts: Record<string, { startPct: number; pct: number }> = {};
  for (const s of STAGES) {
    const [count] = data[s.key] as Pair;
    const pct = total > 0 ? (count / total) * 100 : 0;
    stagePcts[s.key] = { startPct: cumulative, pct };
    cumulative += pct;
  }
  const doneEdgePct = stagePcts.done.startPct + stagePcts.done.pct;
  const showDoneBaseline = stagePcts.done.pct > 0;

  return (
    <div
      data-testid="wip-pipeline"
      style={{
        background: "var(--s1)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: 16,
        height: "100%",
        position: "relative",
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
          <div style={{ position: "relative", marginTop: showDoneBaseline ? 18 : 0 }}>
            <div
              style={{
                display: "flex",
                height: BAR_HEIGHT,
                borderRadius: 4,
                overflow: "hidden",
              }}
            >
              {STAGES.map(({ key, label, color, pattern }) => {
                const [count, delta] = data[key] as Pair;
                const pct = stagePcts[key].pct;
                if (pct === 0) return null;
                const isTerminated = key === "terminated";
                return (
                  <div
                    key={key}
                    data-testid={`wip-segment-${key}`}
                    data-stage={key}
                    onMouseEnter={(e) =>
                      setHover({
                        stageKey: key,
                        label,
                        count,
                        pct,
                        delta,
                        x: e.clientX,
                        y: e.clientY,
                      })
                    }
                    onMouseMove={(e) =>
                      setHover((prev) =>
                        prev && prev.stageKey === key
                          ? { ...prev, x: e.clientX, y: e.clientY }
                          : prev
                      )
                    }
                    onMouseLeave={() => setHover(null)}
                    style={{
                      width: `${pct}%`,
                      background: color,
                      backgroundImage: pattern,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: "white",
                      fontSize: 11,
                      fontFamily: "monospace",
                      fontWeight: 600,
                      // 45deg stripes need a sturdy base color underneath, which
                      // is already set via `background` above. The pattern
                      // overlays on top.
                      cursor: "pointer",
                      ...(isTerminated ? { backgroundColor: "var(--red)" } : {}),
                    }}
                  >
                    {pct >= 8 ? `${Math.round(pct)}%` : null}
                  </div>
                );
              })}
            </div>

            {showDoneBaseline && (
              <>
                <div
                  data-testid="done-baseline-marker"
                  style={{
                    position: "absolute",
                    top: 0,
                    left: `${doneEdgePct}%`,
                    width: 2,
                    height: BAR_HEIGHT,
                    background: "white",
                  }}
                />
                <div
                  style={{
                    position: "absolute",
                    top: -16,
                    left: `${doneEdgePct}%`,
                    transform: "translateX(-50%)",
                    fontSize: 11,
                    color: "var(--text3)",
                    whiteSpace: "nowrap",
                    fontFamily: "monospace",
                  }}
                >
                  本日完工 baseline
                </div>
              </>
            )}
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

      {hover && (
        <div
          data-testid="wip-tooltip"
          style={{
            position: "fixed",
            top: hover.y + 12,
            left: hover.x + 12,
            background: "#0a0a0a",
            color: "white",
            fontSize: 11,
            padding: "4px 8px",
            borderRadius: 4,
            pointerEvents: "none",
            zIndex: 10,
            fontFamily: "monospace",
          }}
        >
          {hover.label} · {hover.count} · {Math.round(hover.pct)}% ·{" "}
          {hover.delta > 0
            ? `↑${hover.delta}`
            : hover.delta < 0
              ? `↓${Math.abs(hover.delta)}`
              : "→"}
        </div>
      )}
    </div>
  );
}

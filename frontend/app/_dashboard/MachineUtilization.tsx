"use client";

import type { MachineHeatmap as MachineHeatmapData, MachineGrid } from "@/types/dashboard";

// Status fill color for the util bar — used only for statuses that report
// real (or approximated) utilization. faulty/disabled use a stripe pattern
// instead because the machine isn't producing usable util data.
const STATUS_COLOR: Record<string, string> = {
  in_use: "var(--blue)",
  idle: "var(--text3)",
  maintenance: "var(--orange)",
};

// Stripe patterns for statuses where util% is meaningless. The bar fills the
// full row so the visual weight matches other rows and signals "this machine
// is out of rotation".
const STATUS_PATTERN: Record<string, string> = {
  faulty:
    "repeating-linear-gradient(45deg, var(--red) 0 6px, rgba(0,0,0,0.4) 6px 10px)",
  disabled:
    "repeating-linear-gradient(45deg, #3a3a3a 0 6px, rgba(255,255,255,0.08) 6px 10px)",
};

// Display label for status (CN). Backend ships canonical English; we render CN.
const STATUS_LABEL: Record<string, string> = {
  in_use: "使用中",
  idle: "閒置",
  maintenance: "保養中",
  faulty: "故障中",
  disabled: "停用",
};

const PATTERN_STATUSES = new Set(["faulty", "disabled"]);

// Approximate per-machine util from today_hours over an 8h shift baseline.
// Backend has no real per-machine util yet — treat 8h as 100%. Capped.
function machineUtilPct(m: MachineGrid): number {
  const raw = (m.today_hours / 8) * 100;
  if (!Number.isFinite(raw) || raw < 0) return 0;
  return Math.min(100, Math.round(raw));
}

function MachineRow({
  m,
  showLabPrefix,
}: {
  m: MachineGrid;
  showLabPrefix: boolean;
}) {
  const isPattern = PATTERN_STATUSES.has(m.status);
  const pct = isPattern ? null : machineUtilPct(m);
  const pattern = STATUS_PATTERN[m.status];
  const fillColor = STATUS_COLOR[m.status] || "var(--text3)";
  const label = STATUS_LABEL[m.status] ?? m.status;

  return (
    <button
      data-testid={`machine-row-${m.machine_id}`}
      data-status={m.status}
      onClick={() => {
        window.location.href = `/machine?id=${m.machine_id}`;
      }}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        background: "transparent",
        border: "none",
        padding: "4px 0",
        cursor: "pointer",
        textAlign: "left",
        color: "var(--text)",
        width: "100%",
      }}
    >
      {showLabPrefix && (
        <span
          style={{
            fontSize: 11,
            color: "var(--text3)",
            fontFamily: "monospace",
            width: 56,
            flexShrink: 0,
          }}
        >
          {m.lab_name}
        </span>
      )}
      <span
        style={{
          fontSize: 12,
          color: "var(--text2)",
          fontFamily: "monospace",
          width: 80,
          flexShrink: 0,
        }}
      >
        {m.machine_no}
      </span>
      {/* The util bar container. Fixed height; the fill div sits inside. */}
      <div
        data-testid={`machine-bar-${m.machine_id}`}
        style={{
          flex: 1,
          height: 12,
          background: "var(--s2)",
          borderRadius: 2,
          overflow: "hidden",
          minWidth: 40,
        }}
      >
        {isPattern ? (
          <div
            data-testid={`machine-bar-fill-${m.machine_id}`}
            style={{
              width: "100%",
              height: "100%",
              background: pattern,
            }}
          />
        ) : (
          <div
            data-testid={`machine-bar-fill-${m.machine_id}`}
            style={{
              width: `${pct}%`,
              height: "100%",
              background: fillColor,
            }}
          />
        )}
      </div>
      <span
        style={{
          fontSize: 11,
          color: "var(--text2)",
          fontFamily: "monospace",
          width: 32,
          textAlign: "right",
          flexShrink: 0,
        }}
      >
        {pct === null ? "—" : `${pct}%`}
      </span>
      <span
        style={{
          fontSize: 11,
          color: "var(--text2)",
          width: 56,
          flexShrink: 0,
        }}
      >
        {label}
      </span>
    </button>
  );
}

export default function MachineUtilization({
  data,
  showLabPrefix,
}: {
  data: MachineHeatmapData;
  showLabPrefix: boolean;
}) {
  // Flatten by_lab into one ordered list. Within each lab we keep the
  // backend's order; labs are sorted alphabetically so cross-lab views are
  // stable.
  const labKeys = Object.keys(data.by_lab).sort();
  const machines: MachineGrid[] = labKeys.flatMap((lab) => data.by_lab[lab]);

  return (
    <div
      data-testid="machine-heatmap"
      style={{
        background: "var(--s1)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: 16,
        height: "100%",
        display: "flex",
        flexDirection: "column",
        minHeight: 0,
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: 12,
        }}
      >
        <h3 style={{ margin: 0, fontSize: 14 }}>機台狀態</h3>
        <span
          style={{
            fontSize: 12,
            color: "var(--text3)",
            fontFamily: "monospace",
          }}
        >
          avg util {data.avg_utilization_pct}% · in_use {data.in_use_count}/
          {data.total_count}
        </span>
      </div>
      {data.total_count === 0 ? (
        <div
          style={{
            color: "var(--text3)",
            fontSize: 12,
            textAlign: "center",
            padding: 24,
          }}
        >
          無機台資料
        </div>
      ) : (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 4,
            overflowY: "auto",
            flex: 1,
          }}
        >
          {machines.map((m) => (
            <MachineRow
              key={m.machine_id}
              m={m}
              showLabPrefix={showLabPrefix}
            />
          ))}
        </div>
      )}
    </div>
  );
}

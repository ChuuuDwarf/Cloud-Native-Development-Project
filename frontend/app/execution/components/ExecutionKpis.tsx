import KpiCard from "@/components/ui/KpiCard";
import { KPI_CARDS } from "../constants";
import { kpiGridStyle } from "../styles";

export default function ExecutionKpis({ kpi }: { kpi: Record<string, number> }) {
  return (
    <div style={kpiGridStyle}>
      {KPI_CARDS.map((c) => (
        <KpiCard
          key={c.key}
          label={c.label}
          value={kpi[c.key] ?? 0}
          color={c.color}
          icon={c.icon}
        />
      ))}
    </div>
  );
}

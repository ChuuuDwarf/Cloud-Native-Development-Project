"""Pydantic v2 DTOs for the supervisor dashboard snapshot.

Mirrored in ``frontend/src/types/dashboard.ts``. The single ``GET /api/dashboard``
endpoint always returns a complete :class:`DashboardSnapshot`; widgets that do
not apply to the caller's role come back as ``None`` rather than an empty list
so the frontend can pick which Col 3 panel to mount.

Field naming is snake_case on the wire (Pydantic default); the existing FE
typing layer maps both casings, so we don't ship aliases here.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.common.enums import Severity

ThresholdColor = Literal["neutral", "orange", "red"]


class KpiCard(BaseModel):
    value: int
    delta_24h: int = Field(
        description="value − value_at(now-24h); positive=up, 0=flat, negative=down"
    )
    threshold_color: ThresholdColor = "neutral"
    sparkline_24h: list[int] | None = Field(
        default=None,
        description=(
            "24 hourly counts ending at the current hour, oldest first. "
            "``None`` for state-type KPIs (待簽 / 告警) that have no hourly "
            "history — the FE skips ``<LineChart>`` rendering in that case."
        ),
    )


class KpiBar(BaseModel):
    new_orders: KpiCard
    completed: KpiCard
    returned: KpiCard
    pending_approval: KpiCard
    open_critical_high_issues: KpiCard


class MachineGrid(BaseModel):
    machine_id: str
    machine_no: str
    lab_name: str
    status: str  # canonical English MachineStatus value
    today_hours: float
    current_recipe: str | None = None
    current_operator: str | None = None
    est_completion_at: datetime | None = None


class MachineHeatmap(BaseModel):
    by_lab: dict[str, list[MachineGrid]]
    avg_utilization_pct: int = Field(ge=0, le=100)
    in_use_count: int
    total_count: int
    per_lab_util_pct: dict[str, int] = Field(
        default_factory=dict,
        description=(
            "Per-lab utilization percent (0..100), keyed by lab display name "
            "to match ``by_lab`` keys. Lab supervisors see one entry (their "
            "own lab); cross-lab viewers see every lab present in ``by_lab``."
        ),
    )


class WipPipeline(BaseModel):
    total: int
    waiting_dispatch: tuple[int, int]
    dispatched: tuple[int, int]
    in_progress: tuple[int, int]
    awaiting_handoff: tuple[int, int]
    done: tuple[int, int]
    terminated: tuple[int, int]


TriageType = Literal["pending_approval", "escalated_issue", "open_issue"]


class TriageItem(BaseModel):
    type: TriageType
    ref_id: str
    label: str
    lab_name: str | None = None
    severity: Severity | None = None
    created_at: datetime


class EscalationRow(BaseModel):
    issue_id: str
    lab_name: str
    severity: Severity
    escalation_level: int
    title: str
    escalated_at: datetime


class CompletionRow(BaseModel):
    wip_no: str
    order_no: str
    lab_name: str
    returned_at: datetime


class ThroughputPoint(BaseModel):
    """One bucket of the lab_supervisor's 24h throughput chart.

    ``hour_offset`` is the bucket index (0 = the hour starting at ``now-24h``,
    23 = the current hour). The two counts are scoped to the caller's lab.
    """

    hour_offset: int = Field(ge=0, le=23)
    completed: int = Field(ge=0)
    returned: int = Field(ge=0)


TrendArrow = Literal["up", "flat", "down"]


class LabRow(BaseModel):
    lab_name: str
    completed_today: int
    awaiting_handoff: int
    open_high_critical_issues: int
    avg_utilization_pct: int = Field(ge=0, le=100)
    trend_24h: TrendArrow


class DashboardSnapshot(BaseModel):
    viewer_role: Literal["lab_supervisor", "general_supervisor"]
    viewer_lab: str | None
    generated_at: datetime

    kpi: KpiBar
    machines: MachineHeatmap
    wip_pipeline: WipPipeline
    triage: list[TriageItem]
    recent_escalations: list[EscalationRow]
    # Mutually exclusive based on role: lab_sup gets completions, general_sup gets leaderboard.
    recent_completions: list[CompletionRow] | None
    lab_leaderboard: list[LabRow] | None

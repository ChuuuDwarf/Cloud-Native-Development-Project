"""DashboardService — orchestrates per-widget queries in parallel and assembles
a :class:`DashboardSnapshot` for the caller.

Role-aware projection:

* ``general_supervisor`` / ``system_admin`` → cross-lab view; the Col 3 panel
  returns ``lab_leaderboard`` (and ``recent_completions`` is ``None``).
* ``lab_supervisor`` (+ any other lab-bound supervisor role we add later)
  → scoped to their own lab; Col 3 returns ``recent_completions`` (and
  ``lab_leaderboard`` is ``None``).

Threshold colors and delta arrows are computed here so the wire format is
ready-to-render — the frontend just paints whatever ``threshold_color`` says.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies.auth import CurrentUser
from app.common.dependencies.scope import resolve_user_lab_codes
from app.modules.dashboard.repository import DashboardRepository
from app.modules.dashboard.schemas import (
    CompletionRow,
    DashboardSnapshot,
    EscalationRow,
    KpiBar,
    KpiCard,
    LabRow,
    MachineGrid,
    MachineHeatmap,
    ThresholdColor,
    ThroughputPoint,
    TriageItem,
    TriageType,
    WipPipeline,
)

# Threshold rules from the design spec (Section 1):
# - 待簽 > 5 → orange
# - 未結告警 > 0 → orange
# (no red threshold defined yet; we leave room for one if tuned later)
# TODO: read from system_settings.alertRules so admins can tune without code edits.
_PENDING_APPROVAL_ORANGE_AT = 6
# TODO: read from system_settings.alertRules.
_OPEN_ISSUES_ORANGE_AT = 1


def _is_cross_lab(user: CurrentUser) -> bool:
    """Whether the caller sees every lab (general_supervisor / system_admin /
    a magic-wildcard permission)."""
    if "*" in user.permissions:
        return True
    return user.role in ("system_admin", "general_supervisor")


def _viewer_role(user: CurrentUser) -> str:
    return "general_supervisor" if _is_cross_lab(user) else "lab_supervisor"


def _threshold(value: int, *, orange_at: int | None, red_at: int | None) -> ThresholdColor:
    if red_at is not None and value >= red_at:
        return "red"
    if orange_at is not None and value >= orange_at:
        return "orange"
    return "neutral"


def _delta(today: int, yesterday: int) -> int:
    return today - yesterday


class DashboardService:
    """Single ``compute_snapshot`` entrypoint — no other public methods.

    The service holds the AsyncSession; the repository wraps it. Widget
    queries run concurrently via ``asyncio.gather`` since they share no
    write paths and the read I/O dominates wall time.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = DashboardRepository(session)

    async def compute_snapshot(self, user: CurrentUser) -> DashboardSnapshot:
        lab_codes = await resolve_user_lab_codes(self._session, user)
        cross_lab = lab_codes is None

        # Fire widget queries in parallel — each is independent. Conditional
        # widgets resolve to None via ``_none_async`` to keep the gather call
        # uniform.
        #
        # Phase H additions:
        # - 3 hourly_buckets calls feed KPI sparklines (only the flow KPIs:
        #   new_orders / completed / returned — state KPIs have no history).
        # - ``throughput_24h`` only fires for lab_supervisor; cross-lab viewers
        #   get the leaderboard instead, so we'd waste the query.
        # - ``per_lab_util`` always fires — feeds MachineHeatmap mini bars
        #   for both roles.
        (
            new_orders,
            completed,
            returned,
            pending_appr,
            open_issues_count,
            machine_rows,
            pipeline_counts,
            triage_approvals,
            triage_issues,
            esc_rows,
            comp_rows,
            leaderboard_rows,
            sparkline_new_orders,
            sparkline_completed,
            sparkline_returned,
            throughput_rows,
            per_lab_util,
        ) = await asyncio.gather(
            self._repo.kpi_new_orders(lab_codes),
            self._repo.kpi_completed_today(lab_codes),
            self._repo.kpi_returned_today(lab_codes),
            self._repo.kpi_pending_approval(lab_codes),
            self._repo.kpi_open_high_critical_issues(lab_codes),
            self._repo.machines(lab_codes),
            self._repo.wip_pipeline_counts(lab_codes),
            self._repo.triage_pending_approvals(lab_codes, limit=5),
            self._repo.triage_unack_issues(lab_codes, user_id=user.id, limit=5),
            self._repo.recent_escalations(lab_codes, limit=5),
            (_none_async() if cross_lab else self._repo.recent_completions(lab_codes, limit=5)),
            (self._repo.lab_leaderboard(limit=5) if cross_lab else _none_async()),
            self._repo.hourly_buckets_new_orders(lab_codes),
            self._repo.hourly_buckets_completed(lab_codes),
            self._repo.hourly_buckets_returned(lab_codes),
            (_none_async() if cross_lab else self._repo.throughput_24h(lab_codes)),
            self._repo.per_lab_util(lab_codes),
        )

        # mypy infers ``asyncio.gather`` results as a union and can't narrow
        # them per-position; the runtime types are guaranteed by the awaited
        # methods, so we silence per-arg here.
        kpi = self._build_kpi(
            new_orders,  # type: ignore[arg-type]
            completed,  # type: ignore[arg-type]
            returned,  # type: ignore[arg-type]
            pending_appr,  # type: ignore[arg-type]
            open_issues_count,  # type: ignore[arg-type]
            sparkline_new_orders=sparkline_new_orders,  # type: ignore[arg-type]
            sparkline_completed=sparkline_completed,  # type: ignore[arg-type]
            sparkline_returned=sparkline_returned,  # type: ignore[arg-type]
        )
        machines = self._build_machines(
            machine_rows,  # type: ignore[arg-type]
            per_lab_util=per_lab_util,  # type: ignore[arg-type]
        )
        pipeline = self._build_pipeline(pipeline_counts)  # type: ignore[arg-type]
        triage = self._build_triage(triage_approvals, triage_issues)  # type: ignore[arg-type]
        escalations = self._build_escalations(esc_rows)  # type: ignore[arg-type]
        completions = (
            self._build_completions(comp_rows)  # type: ignore[arg-type]
            if comp_rows is not None
            else None
        )
        leaderboard = (
            self._build_leaderboard(leaderboard_rows)  # type: ignore[arg-type]
            if leaderboard_rows is not None
            else None
        )
        throughput = (
            self._build_throughput(throughput_rows)  # type: ignore[arg-type]
            if throughput_rows is not None
            else None
        )

        # viewer_lab is the lab_code the caller is scoped to; null for
        # cross-lab viewers so the FE doesn't try to label a single lab.
        viewer_lab = None if cross_lab else (lab_codes[0] if lab_codes else None)

        return DashboardSnapshot(
            viewer_role=_viewer_role(user),  # type: ignore[arg-type]
            viewer_lab=viewer_lab,
            generated_at=datetime.now(UTC),
            kpi=kpi,
            machines=machines,
            wip_pipeline=pipeline,
            triage=triage,
            recent_escalations=escalations,
            throughput_24h=throughput,
            recent_completions=completions,
            lab_leaderboard=leaderboard,
        )

    # ----------------------------------------------------- widget assemblers

    def _build_kpi(
        self,
        new_orders: tuple[int, int],
        completed: tuple[int, int],
        returned: tuple[int, int],
        pending_appr: int,
        open_issues_count: int,
        *,
        sparkline_new_orders: list[int],
        sparkline_completed: list[int],
        sparkline_returned: list[int],
    ) -> KpiBar:
        return KpiBar(
            new_orders=KpiCard(
                value=new_orders[0],
                delta_24h=_delta(*new_orders),
                sparkline_24h=sparkline_new_orders,
            ),
            completed=KpiCard(
                value=completed[0],
                delta_24h=_delta(*completed),
                sparkline_24h=sparkline_completed,
            ),
            returned=KpiCard(
                value=returned[0],
                delta_24h=_delta(*returned),
                sparkline_24h=sparkline_returned,
            ),
            # State-type KPIs have no hourly history — the FE conditionally
            # renders the background <LineChart> only when sparkline_24h is
            # non-null (see Phase H spec Section 1).
            pending_approval=KpiCard(
                value=pending_appr,
                delta_24h=0,  # not tracked over 24h yet
                threshold_color=_threshold(
                    pending_appr,
                    orange_at=_PENDING_APPROVAL_ORANGE_AT,
                    red_at=None,
                ),
                sparkline_24h=None,
            ),
            open_critical_high_issues=KpiCard(
                value=open_issues_count,
                delta_24h=0,
                threshold_color=_threshold(
                    open_issues_count,
                    orange_at=_OPEN_ISSUES_ORANGE_AT,
                    red_at=None,
                ),
                sparkline_24h=None,
            ),
        )

    def _build_machines(
        self,
        rows: list[Any],
        *,
        per_lab_util: dict[str, int],
    ) -> MachineHeatmap:
        by_lab: dict[str, list[MachineGrid]] = {}
        in_use = 0
        total = 0
        sum_today_hours = 0.0
        for r in rows:
            mid, mno, lab, status, today_hours, recipe, op, eta = r
            grid = MachineGrid(
                machine_id=mid,
                machine_no=mno,
                lab_name=lab,
                status=status,
                today_hours=today_hours,
                current_recipe=recipe,
                current_operator=op,
                est_completion_at=eta,
            )
            by_lab.setdefault(lab, []).append(grid)
            total += 1
            if status == "in_use":
                in_use += 1
            sum_today_hours += today_hours
        # avg util = sum_today_hours / (total * 8h) * 100, clamped 0–100.
        avg_util = int(min(100, max(0, (sum_today_hours / (total * 8)) * 100))) if total else 0
        # Limit ``per_lab_util_pct`` to labs that surface a machine grid so the
        # FE doesn't see stray keys for labs absent from ``by_lab`` (e.g. when
        # a scoped query yields no machines for the lab_supervisor's lab).
        per_lab_util_filtered = {
            lab_name: per_lab_util[lab_name] for lab_name in by_lab if lab_name in per_lab_util
        }
        return MachineHeatmap(
            by_lab=by_lab,
            avg_utilization_pct=avg_util,
            in_use_count=in_use,
            total_count=total,
            per_lab_util_pct=per_lab_util_filtered,
        )

    def _build_pipeline(self, counts: dict[str, tuple[int, int]]) -> WipPipeline:
        total = sum(c[0] for c in counts.values())
        return WipPipeline(
            total=total,
            waiting_dispatch=counts["waiting_dispatch"],
            dispatched=counts["dispatched"],
            in_progress=counts["in_progress"],
            awaiting_handoff=counts["awaiting_handoff"],
            done=counts["done"],
            terminated=counts["terminated"],
        )

    def _build_triage(self, approvals: list[Any], issues: list[Any]) -> list[TriageItem]:
        items: list[TriageItem] = []
        for r in approvals:
            order_no, applicant, created_at = r
            label = f"{order_no} · {applicant or ''}".strip(" ·")
            items.append(
                TriageItem(
                    type="pending_approval",
                    ref_id=order_no,
                    label=label,
                    lab_name=None,
                    severity=None,
                    created_at=created_at,
                )
            )
        for r in issues:
            iid, status, severity, _level, lab_code, title, created_at = r
            triage_type: TriageType = "escalated_issue" if status == "escalated" else "open_issue"
            items.append(
                TriageItem(
                    type=triage_type,
                    ref_id=str(iid),
                    label=title,
                    lab_name=lab_code,
                    severity=severity,
                    created_at=created_at,
                )
            )
        # Limit to 5 after merge; the repo already pre-sorted each source so
        # we preserve that order — approvals first (oldest first), then
        # escalated/critical issues.
        return items[:5]

    def _build_escalations(self, rows: list[Any]) -> list[EscalationRow]:
        return [
            EscalationRow(
                issue_id=str(r[0]),
                lab_name=r[1],
                severity=r[2],
                escalation_level=r[3],
                title=r[4],
                escalated_at=r[5],
            )
            for r in rows
        ]

    def _build_completions(self, rows: list[Any]) -> list[CompletionRow]:
        return [
            CompletionRow(wip_no=r[0], order_no=r[1], lab_name=r[2], returned_at=r[3]) for r in rows
        ]

    def _build_throughput(self, rows: list[tuple[int, int, int]]) -> list[ThroughputPoint]:
        return [ThroughputPoint(hour_offset=r[0], completed=r[1], returned=r[2]) for r in rows]

    def _build_leaderboard(self, rows: list[Any]) -> list[LabRow]:
        return [
            LabRow(
                lab_name=r[0],
                completed_today=r[1],
                awaiting_handoff=r[2],
                open_high_critical_issues=r[3],
                avg_utilization_pct=r[4],
                trend_24h="flat",  # no historical snapshot yet
            )
            for r in rows
        ]


async def _none_async() -> None:
    """``asyncio.gather`` requires every arg to be awaitable; this is a no-op
    that produces ``None`` for widgets the caller's role excludes."""
    return None

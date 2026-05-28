"""Per-widget read queries for the supervisor dashboard.

Every method takes ``lab_codes: list[str] | None`` — ``None`` means cross-lab
(no filter, see all labs); a list of lab codes (e.g. ``["LAB-A"]``) scopes to
those labs only. The service layer resolves the caller's lab visibility once
via ``resolve_user_lab_codes()`` and passes the result here.

Repository methods return plain Python primitives or ``Sequence[Row]``; the
service layer maps to schemas. Keeping repository pure-SQL makes it cheap to
unit-test against the seed corpus and lets the service own widget-shape
concerns.

Schema-driven adaptations vs. the design spec:

* ``Wip.lab_name`` stores the lab's **display name** (e.g. ``電性測試實驗室``),
  not the short code — so this module resolves ``lab_codes`` through
  ``labs.code → labs.name`` when filtering Wip queries.
* ``Machine.status`` is stored as the Chinese display string (``使用中`` etc.);
  we accept ``MachineStatus`` enum values for the service-side count but
  callers should consult :data:`MACHINE_STATUS_CN_TO_EN` to translate.
* ``Report.status`` is stored as the D-team Chinese display string
  (``已回傳`` for RETURNED) — see ``REPORT_ZH`` in ``app.common.enums.role_d_zh``.
* ``Report.wip_id`` holds the business ``wip_no`` (string), not a UUID FK.
* ``Wip.status`` uses English values matching B's DB CHECK constraint:
  ``waiting_schedule / scheduled / dispatched / running / paused / completed
  / terminated / cancelled``.
* ``OrderModel.applicant_id`` is the creator handle (no ``created_by`` column).

Issue acknowledgements are derived from the ``Notification`` table rather than
a dedicated ack table: an issue is "unacked by user X" if X has no
notification for that issue with ``status = READ``. See
``app.repos.issues.list_acknowledgements`` for the same pattern.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, case, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import (
    IssueStatus,
    MachineStatus,
    NotificationStatus,
    ReportStatus,
    Severity,
)
from app.common.enums.order_status import OrderStatus
from app.common.enums.role_d_zh import REPORT_ZH
from app.db.models.issues import Issue
from app.db.models.labs import Lab
from app.db.models.machines import Dispatch, Machine
from app.db.models.notifications import Notification
from app.db.models.order_management import OrderItemModel, OrderModel
from app.db.models.reports import Report
from app.db.models.wips import Wip

_DAY = timedelta(hours=24)

# DB-side WIP status values (B's CHECK constraint vocabulary — see
# ``app/db/models/wips.py``: 'created', 'waiting_schedule', 'scheduled',
# 'dispatched', 'running', 'paused', 'completed', 'terminated', 'cancelled').
# Status literals are hardcoded here because ``app.common.enums.WipStatus``
# was authored before B's CHECK constraint landed and now uses values
# (``unloaded``, ``waiting_confirm``, ``waiting_dispatch``, …) that the DB
# never stores — relying on those constants silently produced empty buckets.
#
# ``created`` and ``cancelled`` are deliberately NOT placed in any bucket:
# the spec's WIP pipeline starts at "waiting for dispatch" and ends at
# completed/terminated. Cancelled WIPs are a write-off, not a delivery state.
_WIP_WAITING_DISPATCH = "waiting_schedule"
_WIP_SCHEDULED_STATES = ("scheduled", "dispatched")
_WIP_IN_PROGRESS_STATES = ("running", "paused")
_WIP_COMPLETED = "completed"
_WIP_TERMINATED = "terminated"

# Reports persist Chinese status strings (D-team convention).
_REPORT_RETURNED_ZH = REPORT_ZH[ReportStatus.RETURNED]

# Issue statuses that count as "open" for the KPI bar and triage list.
_OPEN_ISSUE_STATUSES = (
    IssueStatus.OPEN.value,
    IssueStatus.ASSIGNED.value,
    IssueStatus.ESCALATED.value,
)
_HIGH_CRITICAL = (Severity.HIGH.value, Severity.CRITICAL.value)

# Machine status (Chinese) ↔ canonical English.
MACHINE_STATUS_CN_TO_EN: dict[str, str] = {
    "閒置": MachineStatus.IDLE.value,
    "使用中": MachineStatus.IN_USE.value,
    "保養中": MachineStatus.MAINTENANCE.value,
    "故障中": MachineStatus.FAULTY.value,
    "停用": MachineStatus.DISABLED.value,
}


def _now_aware() -> datetime:
    """``datetime.now(UTC)``-aware. Use for columns declared as
    ``DateTime(timezone=True)`` — e.g. ``Issue.created_at`` / ``updated_at``,
    ``OrderModel.created_at``.
    """
    return datetime.now(UTC)


def _now_naive() -> datetime:
    """tz-naive ``now``. Use for columns declared as plain ``TIMESTAMP`` —
    e.g. ``Wip.completed_at`` (B's migration) and ``Report.created_at``
    (D's migration). Mixing a tz-aware datetime against a naive column
    triggers asyncpg ``DataError`` at execute time.
    """
    return datetime.now(UTC).replace(tzinfo=None)


def _rolling_windows(*, naive: bool = False) -> tuple[datetime, datetime, datetime]:
    """Return ``(now, today_lower, yday_lower)`` for the spec's rolling 24h
    delta calculation:

    * ``today`` window  = ``[today_lower, now)``  — last 24h
    * ``yesterday`` window = ``[yday_lower, today_lower)`` — the 24h before that

    Set ``naive=True`` for columns declared as plain ``TIMESTAMP``.
    """
    now = _now_naive() if naive else _now_aware()
    today_lower = now - timedelta(hours=24)
    yday_lower = now - timedelta(hours=48)
    return now, today_lower, yday_lower


class DashboardRepository:
    """Read-side queries for the dashboard. One method per widget concern."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------ helpers

    async def lab_names_for_codes(self, lab_codes: list[str] | None) -> list[str] | None:
        """Resolve a list of lab codes (``["LAB-A"]``) to their Chinese display
        names so they can be matched against ``Wip.lab_name`` / ``OrderModel``
        descendants that store the display name.

        ``None`` passes through (means "all labs" / no filter). Empty input
        returns an empty list (caller should short-circuit to zero counts).
        """
        if lab_codes is None:
            return None
        if not lab_codes:
            return []
        rows = (await self._session.execute(select(Lab.name).where(Lab.code.in_(lab_codes)))).all()
        return [r[0] for r in rows]

    # ----------------------------------------------------------------- KPI bar

    async def kpi_new_orders(self, lab_codes: list[str] | None) -> tuple[int, int]:
        """``(today_count, yesterday_count)`` — orders whose ``created_at`` falls
        in the trailing 24h window vs. the 24h before that. Both windows are
        rolling: ``[now-24h, now)`` and ``[now-48h, now-24h)``. Matches the
        spec's rolling-24h delta calculation; the old calendar-day approach
        compared partial-today vs full-yesterday and read as negative all
        morning.

        Scoping walks ``OrderItemModel.lab_id`` (a short String code like
        ``"LAB-A"``) — see ``backend/app/repos/order_repo.py``. Going through
        Wip.lab_name would under-count orders that have not yet been split
        into WIPs (notably PENDING_APPROVAL).
        """
        now, today_lower, yday_lower = _rolling_windows()

        if lab_codes is None:
            today = await self._session.scalar(
                select(func.count())
                .select_from(OrderModel)
                .where(OrderModel.created_at >= today_lower, OrderModel.created_at < now)
            )
            yday = await self._session.scalar(
                select(func.count())
                .select_from(OrderModel)
                .where(
                    OrderModel.created_at >= yday_lower,
                    OrderModel.created_at < today_lower,
                )
            )
            return int(today or 0), int(yday or 0)

        # Scoped: count distinct orders whose items target the caller's labs.
        base = (
            select(func.count(func.distinct(OrderModel.id)))
            .select_from(OrderModel)
            .join(OrderItemModel, OrderItemModel.order_id == OrderModel.id)
            .where(OrderItemModel.lab_id.in_(lab_codes))
        )
        today = await self._session.scalar(
            base.where(OrderModel.created_at >= today_lower, OrderModel.created_at < now)
        )
        yday = await self._session.scalar(
            base.where(
                OrderModel.created_at >= yday_lower,
                OrderModel.created_at < today_lower,
            )
        )
        return int(today or 0), int(yday or 0)

    async def kpi_completed_today(self, lab_codes: list[str] | None) -> tuple[int, int]:
        """``(today, yesterday)`` WIPs whose ``completed_at`` falls in window.

        ``Wip.completed_at`` is a naive TIMESTAMP — use naive bounds.
        """
        now, today_lower, yday_lower = _rolling_windows(naive=True)
        base_today = (
            select(func.count())
            .select_from(Wip)
            .where(
                Wip.status == _WIP_COMPLETED,
                Wip.completed_at >= today_lower,
                Wip.completed_at < now,
            )
        )
        base_yday = (
            select(func.count())
            .select_from(Wip)
            .where(
                Wip.status == _WIP_COMPLETED,
                Wip.completed_at >= yday_lower,
                Wip.completed_at < today_lower,
            )
        )
        if lab_codes is not None:
            lab_names = await self.lab_names_for_codes(lab_codes)
            if not lab_names:
                return 0, 0
            base_today = base_today.where(Wip.lab_name.in_(lab_names))
            base_yday = base_yday.where(Wip.lab_name.in_(lab_names))
        today = await self._session.scalar(base_today)
        yday = await self._session.scalar(base_yday)
        return int(today or 0), int(yday or 0)

    async def kpi_returned_today(self, lab_codes: list[str] | None) -> tuple[int, int]:
        """``(today, yesterday)`` reports whose status is RETURNED.

        ``Report.created_at`` is the only timestamp on the model; we use it as
        a proxy for "returned at". This will under-count if a report is updated
        from PUBLISHED → RETURNED long after creation, but matches the existing
        ``app.modules.reports`` flow where reports are created in DRAFT and
        only quickly transition. The column is a naive TIMESTAMP — use naive
        bounds.
        """
        now, today_lower, yday_lower = _rolling_windows(naive=True)
        base_today = (
            select(func.count())
            .select_from(Report)
            .where(
                Report.status == _REPORT_RETURNED_ZH,
                Report.created_at >= today_lower,
                Report.created_at < now,
            )
        )
        base_yday = (
            select(func.count())
            .select_from(Report)
            .where(
                Report.status == _REPORT_RETURNED_ZH,
                Report.created_at >= yday_lower,
                Report.created_at < today_lower,
            )
        )
        if lab_codes is not None:
            lab_names = await self.lab_names_for_codes(lab_codes)
            if not lab_names:
                return 0, 0
            # Report.wip_id holds the wip_no business code (string).
            base_today = base_today.join(Wip, Wip.wip_no == Report.wip_id).where(
                Wip.lab_name.in_(lab_names)
            )
            base_yday = base_yday.join(Wip, Wip.wip_no == Report.wip_id).where(
                Wip.lab_name.in_(lab_names)
            )
        today = await self._session.scalar(base_today)
        yday = await self._session.scalar(base_yday)
        return int(today or 0), int(yday or 0)

    async def kpi_pending_approval(self, lab_codes: list[str] | None) -> int:
        """Current count of orders awaiting supervisor approval.

        Scoped via ``OrderItemModel.lab_id`` (lab code) rather than ``Wip``,
        because PENDING_APPROVAL orders have not been split into WIPs yet
        — joining through Wip would silently report 0 for every lab.
        """
        base = (
            select(func.count())
            .select_from(OrderModel)
            .where(OrderModel.status == OrderStatus.PENDING_APPROVAL.value)
        )
        if lab_codes is not None:
            base = (
                select(func.count(func.distinct(OrderModel.id)))
                .select_from(OrderModel)
                .join(OrderItemModel, OrderItemModel.order_id == OrderModel.id)
                .where(
                    OrderModel.status == OrderStatus.PENDING_APPROVAL.value,
                    OrderItemModel.lab_id.in_(lab_codes),
                )
            )
        return int(await self._session.scalar(base) or 0)

    async def kpi_open_high_critical_issues(self, lab_codes: list[str] | None) -> int:
        """Open + escalated + assigned issues at high/critical severity."""
        base = (
            select(func.count())
            .select_from(Issue)
            .where(
                Issue.status.in_(_OPEN_ISSUE_STATUSES),
                Issue.severity.in_(_HIGH_CRITICAL),
            )
        )
        if lab_codes is not None:
            base = base.join(Lab, Lab.id == Issue.lab_id).where(Lab.code.in_(lab_codes))
        return int(await self._session.scalar(base) or 0)

    # --------------------------------------------------------------- machines

    async def machines(self, lab_codes: list[str] | None) -> Sequence[Any]:
        """Return ``(machine_id, machine_no, lab_name, status_en, today_hours,
        current_recipe, current_operator, est_completion_at)`` rows.

        ``lab_name`` is the lab's display name (e.g. ``材料分析實驗室``),
        resolved via ``Machine.lab → Lab.code`` so every dashboard widget
        labels labs the same way (Wip.lab_name already stores the display
        name). Machines whose ``lab`` code has no matching ``labs`` row fall
        back to the raw code rather than disappearing.

        ``today_hours`` is a best-effort proxy from ``Machine.utilization``
        (a 0-100 percent) — converted to "hours of an 8h day" so the service
        can build avg utilization without a real WipExecution lookup. The
        recipe/operator/eta columns are not yet tracked on Machine; return
        ``None`` for now so the schema is honoured.
        """
        stmt = select(
            Machine.id,
            Machine.machine_id,
            Machine.lab,
            Lab.name,
            Machine.status,
            Machine.utilization,
        ).outerjoin(Lab, Lab.code == Machine.lab)
        if lab_codes is not None:
            stmt = stmt.where(Machine.lab.in_(lab_codes))
        rows = (await self._session.execute(stmt)).all()
        return [
            (
                str(r[0]),
                r[1],
                r[3] or r[2],  # prefer Lab.name; fall back to raw code
                MACHINE_STATUS_CN_TO_EN.get(r[4], r[4]),
                float(r[5] or 0) / 100.0 * 8.0,  # crude % → hours-of-day
                None,
                None,
                None,
            )
            for r in rows
        ]

    # ------------------------------------------------------------ WIP pipeline

    async def wip_pipeline_counts(self, lab_codes: list[str] | None) -> dict[str, tuple[int, int]]:
        """Per-stage current counts (delta_24h is 0 — we don't snapshot history).

        Stage definitions follow the design spec (Section 3) but use the actual
        DB enum values:

        * ``waiting_dispatch`` — WIP at ``waiting_schedule`` with no Dispatch row.
        * ``dispatched``        — WIP at ``scheduled`` / ``dispatched``.
        * ``in_progress``       — WIP at ``running`` / ``unloaded`` / ``waiting_confirm``.
        * ``awaiting_handoff``  — WIP ``completed`` AND report RETURNED AND order
          not yet in WAITING_PICKUP / CLOSED (== spec's "待傳" stage).
        * ``done``              — WIP ``completed`` AND order in
          WAITING_PICKUP / CLOSED.
        * ``terminated``        — WIP at ``terminated``.
        """
        lab_names = await self.lab_names_for_codes(lab_codes) if lab_codes is not None else None
        if lab_codes is not None and not lab_names:
            zero: tuple[int, int] = (0, 0)
            return {
                "waiting_dispatch": zero,
                "dispatched": zero,
                "in_progress": zero,
                "awaiting_handoff": zero,
                "done": zero,
                "terminated": zero,
            }

        def _apply_wip_scope(stmt):
            if lab_names is None:
                return stmt
            return stmt.where(Wip.lab_name.in_(lab_names))

        # waiting_dispatch: WIP waiting_schedule AND no Dispatch row.
        wd_stmt = (
            select(func.count())
            .select_from(Wip)
            .outerjoin(Dispatch, Dispatch.wip_id == Wip.wip_no)
            .where(Wip.status == _WIP_WAITING_DISPATCH, Dispatch.id.is_(None))
        )
        waiting_dispatch_now = int(await self._session.scalar(_apply_wip_scope(wd_stmt)) or 0)

        # dispatched: WIP scheduled/dispatched.
        d_stmt = select(func.count()).select_from(Wip).where(Wip.status.in_(_WIP_SCHEDULED_STATES))
        dispatched_now = int(await self._session.scalar(_apply_wip_scope(d_stmt)) or 0)

        # in_progress.
        ip_stmt = (
            select(func.count()).select_from(Wip).where(Wip.status.in_(_WIP_IN_PROGRESS_STATES))
        )
        in_progress_now = int(await self._session.scalar(_apply_wip_scope(ip_stmt)) or 0)

        # terminated.
        t_stmt = select(func.count()).select_from(Wip).where(Wip.status == _WIP_TERMINATED)
        terminated_now = int(await self._session.scalar(_apply_wip_scope(t_stmt)) or 0)

        # awaiting_handoff: completed + report returned + order NOT in
        # (waiting_pickup, closed). Report.wip_id holds the business wip_no.
        # Use EXISTS instead of JOIN so a WIP with multiple RETURNED reports
        # (allowed by the ReportVersion model) counts exactly once.
        report_returned_exists = exists().where(
            Report.wip_id == Wip.wip_no,
            Report.status == _REPORT_RETURNED_ZH,
        )
        ah_stmt = (
            select(func.count())
            .select_from(Wip)
            .join(OrderModel, OrderModel.order_no == Wip.order_no)
            .where(
                Wip.status == _WIP_COMPLETED,
                report_returned_exists,
                OrderModel.status.notin_(
                    [OrderStatus.WAITING_PICKUP.value, OrderStatus.CLOSED.value]
                ),
            )
        )
        awaiting_handoff_now = int(await self._session.scalar(_apply_wip_scope(ah_stmt)) or 0)

        # done: completed + report returned + order in (waiting_pickup, closed).
        done_stmt = (
            select(func.count())
            .select_from(Wip)
            .join(OrderModel, OrderModel.order_no == Wip.order_no)
            .where(
                Wip.status == _WIP_COMPLETED,
                report_returned_exists,
                OrderModel.status.in_([OrderStatus.WAITING_PICKUP.value, OrderStatus.CLOSED.value]),
            )
        )
        done_now = int(await self._session.scalar(_apply_wip_scope(done_stmt)) or 0)

        # Delta_24h: no historical snapshot, return 0 so the UI shows "→".
        return {
            "waiting_dispatch": (waiting_dispatch_now, 0),
            "dispatched": (dispatched_now, 0),
            "in_progress": (in_progress_now, 0),
            "awaiting_handoff": (awaiting_handoff_now, 0),
            "done": (done_now, 0),
            "terminated": (terminated_now, 0),
        }

    # ----------------------------------------------------------------- triage

    async def triage_pending_approvals(
        self, lab_codes: list[str] | None, limit: int
    ) -> Sequence[Any]:
        """Oldest pending-approval orders first — they need a supervisor's eyes
        most urgently. Returns ``(order_no, applicant_id, created_at)`` rows.

        Scoped via ``OrderItemModel.lab_id`` (lab code) so PENDING_APPROVAL
        orders without WIPs still surface for the right lab supervisor.
        """
        if lab_codes is None:
            stmt = (
                select(OrderModel.order_no, OrderModel.applicant_id, OrderModel.created_at)
                .where(OrderModel.status == OrderStatus.PENDING_APPROVAL.value)
                .order_by(OrderModel.created_at.asc())
                .limit(limit)
            )
            return (await self._session.execute(stmt)).all()

        # Group by order id so an order with multiple items in the caller's
        # labs only appears once.
        stmt = (
            select(OrderModel.order_no, OrderModel.applicant_id, OrderModel.created_at)
            .join(OrderItemModel, OrderItemModel.order_id == OrderModel.id)
            .where(
                OrderModel.status == OrderStatus.PENDING_APPROVAL.value,
                OrderItemModel.lab_id.in_(lab_codes),
            )
            .group_by(
                OrderModel.id, OrderModel.order_no, OrderModel.applicant_id, OrderModel.created_at
            )
            .order_by(OrderModel.created_at.asc())
            .limit(limit)
        )
        return (await self._session.execute(stmt)).all()

    async def triage_unack_issues(
        self, lab_codes: list[str] | None, user_id: Any, limit: int
    ) -> Sequence[Any]:
        """High/critical open issues NOT yet acknowledged by ``user_id``.

        Acknowledgement is derived from the ``Notification`` table (no
        dedicated ack table exists): an issue is "unacked by U" if U has no
        notification for that issue whose status is READ. Mirrors the read
        logic in ``app.repos.issues.list_acknowledgements``.

        Returns ``(issue_id, status, severity, escalation_level, lab_name,
        title, created_at)`` rows, sorted: escalated first, then critical
        first, then newest first. ``lab_name`` is the lab's display name
        (``Lab.name``), keeping every widget's ``lab_name`` column
        consistent with the others.
        """
        # Subquery: issue_ids the user has acked via reading a notification.
        acked_subq = (
            select(Notification.source_id)
            .where(
                Notification.recipient_id == user_id,
                Notification.source_type == "issue",
                Notification.status == NotificationStatus.READ.value,
            )
            .scalar_subquery()
        )

        stmt = (
            select(
                Issue.id,
                Issue.status,
                Issue.severity,
                Issue.escalation_level,
                Lab.name,
                Issue.title,
                Issue.created_at,
            )
            .join(Lab, Lab.id == Issue.lab_id)
            .where(
                Issue.status.in_(_OPEN_ISSUE_STATUSES),
                Issue.severity.in_(_HIGH_CRITICAL),
                # Notification.source_id is a VARCHAR holding the issue UUID.
                func.cast(Issue.id, type_=Notification.source_id.type).notin_(acked_subq),
            )
            .order_by(
                case((Issue.status == IssueStatus.ESCALATED.value, 0), else_=1),
                case((Issue.severity == Severity.CRITICAL.value, 0), else_=1),
                Issue.created_at.desc(),
            )
            .limit(limit)
        )
        if lab_codes is not None:
            stmt = stmt.where(Lab.code.in_(lab_codes))
        return (await self._session.execute(stmt)).all()

    # ------------------------------------------------------------ escalations

    async def recent_escalations(self, lab_codes: list[str] | None, limit: int) -> Sequence[Any]:
        """Last 24h of issues currently at ``escalated`` status.

        ``Issue.updated_at`` acts as the "escalated_at" proxy — the escalation
        worker bumps ``escalation_level`` and updates this timestamp on each
        level transition, so it's the closest available signal without
        introducing a dedicated audit table.

        Returns ``(issue_id, lab_name, severity, escalation_level, title,
        escalated_at)``. ``lab_name`` is the display name (Lab.name) so it
        matches every other widget's ``lab_name`` column.
        """
        cutoff = datetime.now(UTC) - _DAY
        stmt = (
            select(
                Issue.id,
                Lab.name,
                Issue.severity,
                Issue.escalation_level,
                Issue.title,
                Issue.updated_at,
            )
            .join(Lab, Lab.id == Issue.lab_id)
            .where(
                Issue.status == IssueStatus.ESCALATED.value,
                Issue.updated_at >= cutoff,
            )
            .order_by(Issue.updated_at.desc())
            .limit(limit)
        )
        if lab_codes is not None:
            stmt = stmt.where(Lab.code.in_(lab_codes))
        return (await self._session.execute(stmt)).all()

    # ------------------------------------------------------------- completions

    async def recent_completions(self, lab_codes: list[str] | None, limit: int) -> Sequence[Any]:
        """Last 30min of RETURNED reports (per the spec — "Recent Completions"
        is a heads-up panel for lab_supervisor's Col 3).

        Returns ``(wip_no, order_no, lab_name, returned_at)`` rows newest
        first, **deduped per wip_no** — a WIP with multiple RETURNED reports
        shows up once with the latest returned timestamp. Lab scoping passes
        lab codes; the join walks ``Report.wip_id (=wip_no) → Wip.lab_name``.

        ``Report.created_at`` is a naive TIMESTAMP — cutoff is naive too.
        """
        cutoff = _now_naive() - timedelta(minutes=30)
        latest_returned_at = func.max(Report.created_at).label("returned_at")
        stmt = (
            select(Report.wip_id, Wip.order_no, Wip.lab_name, latest_returned_at)
            .join(Wip, Wip.wip_no == Report.wip_id)
            .where(
                Report.status == _REPORT_RETURNED_ZH,
                Report.created_at >= cutoff,
            )
            .group_by(Report.wip_id, Wip.order_no, Wip.lab_name)
            .order_by(latest_returned_at.desc())
            .limit(limit)
        )
        if lab_codes is not None:
            lab_names = await self.lab_names_for_codes(lab_codes)
            if not lab_names:
                return []
            stmt = stmt.where(Wip.lab_name.in_(lab_names))
        return (await self._session.execute(stmt)).all()

    # --------------------------------------------------------- leaderboard

    async def lab_leaderboard(self, limit: int) -> Sequence[Any]:
        """Per-lab today snapshot for the general_supervisor's Col 3.

        Returns rows of ``(lab_name, completed_today, awaiting_handoff,
        open_high_critical_issues, avg_utilization_pct)`` already sorted by
        completed_today descending. Drives every Lab present in the ``labs``
        table so a quiet lab still appears as a zero row instead of being
        silently dropped.

        Utilization comes from ``Machine.utilization`` (per-machine 0-100%)
        averaged per lab; 0 for labs with no machines.
        """
        # Wip.completed_at is naive — use naive bounds. ``completed_today``
        # uses the same rolling 24h window the KPI bar uses.
        _, today_lower, _ = _rolling_windows(naive=True)

        # Get every active lab as the driver so labs without WIPs still appear.
        labs = (
            await self._session.execute(
                select(Lab.code, Lab.name).where(Lab.is_active.is_(True)).order_by(Lab.code)
            )
        ).all()

        # Completed today per lab_name (rolling last 24h).
        completed_rows = (
            await self._session.execute(
                select(Wip.lab_name, func.count())
                .where(Wip.status == _WIP_COMPLETED, Wip.completed_at >= today_lower)
                .group_by(Wip.lab_name)
            )
        ).all()
        completed_by_lab: dict[str, int] = {r[0]: int(r[1]) for r in completed_rows}

        # Awaiting handoff per lab_name. Use EXISTS so a wip with multiple
        # RETURNED reports counts once (mirrors wip_pipeline_counts).
        report_returned_exists = exists().where(
            Report.wip_id == Wip.wip_no,
            Report.status == _REPORT_RETURNED_ZH,
        )
        awaiting_rows = (
            await self._session.execute(
                select(Wip.lab_name, func.count())
                .select_from(Wip)
                .join(OrderModel, OrderModel.order_no == Wip.order_no)
                .where(
                    Wip.status == _WIP_COMPLETED,
                    report_returned_exists,
                    OrderModel.status.notin_(
                        [OrderStatus.WAITING_PICKUP.value, OrderStatus.CLOSED.value]
                    ),
                )
                .group_by(Wip.lab_name)
            )
        ).all()
        awaiting_by_lab: dict[str, int] = {r[0]: int(r[1]) for r in awaiting_rows}

        # Open high/critical issues per Lab (joined via Lab.id).
        issue_rows = (
            await self._session.execute(
                select(Lab.code, Lab.name, func.count(Issue.id))
                .select_from(Lab)
                .outerjoin(
                    Issue,
                    and_(
                        Issue.lab_id == Lab.id,
                        Issue.status.in_(_OPEN_ISSUE_STATUSES),
                        Issue.severity.in_(_HIGH_CRITICAL),
                    ),
                )
                .group_by(Lab.code, Lab.name)
            )
        ).all()
        issues_by_lab_name: dict[str, int] = {r[1]: int(r[2]) for r in issue_rows}

        # Avg utilization per lab (Machine.lab is the lab code).
        util_rows = (
            await self._session.execute(
                select(Machine.lab, func.avg(Machine.utilization)).group_by(Machine.lab)
            )
        ).all()
        util_by_lab_code: dict[str, float] = {r[0]: float(r[1] or 0) for r in util_rows}

        result_rows: list[tuple[str, int, int, int, int]] = []
        for code, name in labs:
            result_rows.append(
                (
                    name,
                    completed_by_lab.get(name, 0),
                    awaiting_by_lab.get(name, 0),
                    issues_by_lab_name.get(name, 0),
                    int(round(util_by_lab_code.get(code, 0.0))),
                )
            )
        result_rows.sort(key=lambda r: r[1], reverse=True)
        return result_rows[:limit]

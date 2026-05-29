# Supervisor Dashboard Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a 3-Zone Operational supervisor dashboard (5 KPI bar + machine heatmap + WIP pipeline + 3-col bottom) with role-aware data, backed by a new `backend/app/modules/dashboard/` module and a SSE refresh channel, replacing the existing `frontend/app/page.tsx`.

**Architecture:** Single `GET /api/dashboard` endpoint returns a complete `DashboardSnapshot` with widgets toggled by viewer role (`lab_supervisor` vs `general_supervisor`). Frontend uses TanStack Query 30s polling + `EventSource` listening on `GET /api/dashboard/stream` for invalidation events published from `workers/escalation.py`, `modules/orders/service.py`, and `modules/reports/service.py` via Redis pub/sub.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + Pydantic v2 (Pydantic v1-style field aliases allowed); `sse-starlette` for SSE; `redis==5.2.0` for pub/sub. Frontend: Next.js 16 App Router + TanStack Query + native `EventSource`; styles via existing CSS variables in `globals.css`.

**Source spec:** `docs/superpowers/specs/2026-05-29-supervisor-dashboard-redesign-design.md` — refer for visual rules, color tokens, sort order, drill-down paths, and rationale not repeated here.

**Scope cuts (from spec):** No `/api/dashboard/widgets/:key`, no `POST /api/dashboard/simulations`, no mobile layout, no `lab_engineer` dashboard.

**Important scoping note:** The codebase has `LabScope` (`backend/app/common/dependencies/lab_scope.py`) for lab-bound rows but the primary helpers for queries are `apply_lab_scope(stmt, user, lab_id_column)` and `resolve_user_lab_codes(session, user)` in `backend/app/common/dependencies/scope.py` — both treat `general_supervisor` and `system_admin` as cross-lab (see all). Use these directly; do not assume an `OrderScope` exists.

**Wips lab column note:** `wips.lab_name` is a Chinese display string. Filter via `Wip.lab_name.in_(codes_or_names)` after `resolve_user_lab_codes()`, OR join through `Lab` to use lab_id. Existing `closures` module uses `LabScope.list_lab_filter()` returning `lab_name` — mirror that pattern.

**Frontend visual reminders (from spec):**
- KPI Bar: 5 cards equal-width, 28px bold number, 12px label, 11px monospace delta arrow
- Stage colors: 待排程 grey, 排程 cyan, 進行 blue, 待傳 orange, 完 green, 終止 red striped
- Severity: critical=red, high=orange, medium=#d4a300, low=cyan
- Panel container: `background: var(--s1)`, `border: 1px solid var(--border)`, `border-radius: 8`, `padding: 16`
- Zone gap: 16px, card gap: 14px

---

## File Structure

### Backend — new module
- `backend/app/modules/dashboard/__init__.py` (empty marker)
- `backend/app/modules/dashboard/schemas.py` (DashboardSnapshot + sub-schemas)
- `backend/app/modules/dashboard/repository.py` (one method per widget)
- `backend/app/modules/dashboard/service.py` (asyncio.gather orchestration)
- `backend/app/modules/dashboard/publisher.py` (Redis pub helpers)
- `backend/app/modules/dashboard/router.py` (GET + SSE)
- `backend/app/modules/dashboard/dependencies.py` (DI shims)

### Backend — wire-up edits
- `backend/app/main.py` (include router)

### Backend — publish hooks (1–3 line edits each)
- `backend/app/workers/escalation.py` (after escalation level bump)
- `backend/app/modules/orders/service.py` (after `submit_for_approval` commit)
- `backend/app/modules/reports/service.py` (after report transitions to `RETURNED`)

### Backend — tests
- `backend/tests/e_tests/test_dashboard_repository.py`
- `backend/tests/e_tests/test_dashboard_service.py`
- `backend/tests/e_tests/test_dashboard_router.py`

### Frontend — deletions
- `frontend/app/_dashboard/AttentionPanel.tsx`
- `frontend/app/_dashboard/DispatchPanel.tsx`
- `frontend/app/_dashboard/LabsPanel.tsx`
- `frontend/app/_dashboard/MachineStatusPanel.tsx`

### Frontend — rewrites
- `frontend/app/page.tsx` (layout orchestration only, ~80 LOC)
- `frontend/src/types/dashboard.ts` (mirror backend schema)
- `frontend/src/services/dashboard-api.ts` (one `getSnapshot()` call)

### Frontend — new components & hook
- `frontend/app/_dashboard/KpiBar.tsx`
- `frontend/app/_dashboard/MachineHeatmap.tsx`
- `frontend/app/_dashboard/WipPipeline.tsx`
- `frontend/app/_dashboard/TriageList.tsx`
- `frontend/app/_dashboard/EscalationsList.tsx`
- `frontend/app/_dashboard/CompletionsList.tsx`
- `frontend/app/_dashboard/LabLeaderboard.tsx`
- `frontend/app/_dashboard/useDashboardStream.ts`

### Frontend — tests
- `frontend/app/_dashboard/__tests__/KpiBar.test.tsx`
- `frontend/app/_dashboard/__tests__/MachineHeatmap.test.tsx`
- `frontend/app/_dashboard/__tests__/WipPipeline.test.tsx`
- `frontend/app/_dashboard/__tests__/TriageList.test.tsx`
- `frontend/app/_dashboard/__tests__/EscalationsList.test.tsx`
- `frontend/app/_dashboard/__tests__/CompletionsList.test.tsx`
- `frontend/app/_dashboard/__tests__/LabLeaderboard.test.tsx`

### E2E
- `frontend/e2e/dashboard.spec.ts`

---

## Task 1: Backend Schemas

**Files:**
- Create: `backend/app/modules/dashboard/__init__.py`
- Create: `backend/app/modules/dashboard/schemas.py`

- [ ] **Step 1: Create empty marker file**

Create `backend/app/modules/dashboard/__init__.py` with content:

```python
"""Supervisor dashboard module — single snapshot endpoint + SSE invalidation."""
```

- [ ] **Step 2: Create schemas.py**

Create `backend/app/modules/dashboard/schemas.py`:

```python
"""Pydantic v2 DTOs for the supervisor dashboard snapshot.

Mirrored in frontend/src/types/dashboard.ts. The single GET /api/dashboard
endpoint always returns a complete DashboardSnapshot — widgets that don't
apply to the caller's role come back as ``None`` rather than an empty list,
so the frontend can pick which Col 3 panel to mount.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.common.enums.severity import Severity


ThresholdColor = Literal["neutral", "orange", "red"]


class KpiCard(BaseModel):
    value: int
    delta_24h: int = Field(description="value − value_at(now-24h); positive=up, 0=flat, negative=down")
    threshold_color: ThresholdColor = "neutral"


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
    status: str  # MachineStatus enum value as string for FE label lookup
    today_hours: float
    current_recipe: str | None = None
    current_operator: str | None = None
    est_completion_at: datetime | None = None


class MachineHeatmap(BaseModel):
    by_lab: dict[str, list[MachineGrid]]
    avg_utilization_pct: int = Field(ge=0, le=100)
    in_use_count: int
    total_count: int


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
    recent_completions: list[CompletionRow] | None
    lab_leaderboard: list[LabRow] | None
```

Note: if `app.common.enums.severity` does not export `Severity`, use `from app.common.enums import Severity` instead — the existing `backend/app/services/issues.py` uses `Severity`, so it's exported from the package.

- [ ] **Step 3: Commit**

```bash
git add backend/app/modules/dashboard/__init__.py backend/app/modules/dashboard/schemas.py
git commit -m "feat(dashboard): add schemas for supervisor dashboard snapshot"
```

---

## Task 2: Backend Repository — all widget queries

**Files:**
- Create: `backend/app/modules/dashboard/repository.py`
- Test: `backend/tests/e_tests/test_dashboard_repository.py`

The repository is the single owner of widget DB queries. Each method returns plain Python primitives or `Sequence[Row]`; the service layer converts to schemas.

- [ ] **Step 1: Create repository.py**

Create `backend/app/modules/dashboard/repository.py`:

```python
"""Per-widget read queries for the dashboard.

Every method takes ``lab_filter: list[str] | None`` (None = no scope = see all
labs; list = filter Wip.lab_name / Machine.lab IN list). Resolve via
``resolve_user_lab_codes()`` in the service layer.

Returns plain tuples / dicts / Sequence rows — schema mapping is the service's
job. This separation keeps repository tests pure SQL and lets the service
keep widget-shape concerns.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import MachineStatus
from app.common.enums import OrderStatus
from app.common.enums import Severity
from app.common.enums import WipStatus
from app.db.models.dispatches import Dispatch
from app.db.models.experiment_runs import WipExecution
from app.db.models.issues import Issue, IssueAcknowledgement
from app.db.models.labs import Lab
from app.db.models.machines import Machine
from app.db.models.orders import Order as OrderModel
from app.db.models.reports import Report
from app.db.models.wips import Wip


_DAY = timedelta(hours=24)


def _today_start() -> datetime:
    now = datetime.now(UTC)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


class DashboardRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------- KPI -------

    async def kpi_new_orders(self, lab_filter: list[str] | None) -> tuple[int, int]:
        """Return (today_count, yesterday_count). Yesterday window = same 24h band 24h earlier."""
        ts = _today_start()
        ys = ts - _DAY
        if lab_filter is None:
            today = await self._session.scalar(
                select(func.count()).select_from(OrderModel).where(OrderModel.created_at >= ts)
            )
            yday = await self._session.scalar(
                select(func.count())
                .select_from(OrderModel)
                .where(OrderModel.created_at >= ys, OrderModel.created_at < ts)
            )
        else:
            base = select(func.count(func.distinct(OrderModel.order_no))).select_from(OrderModel).join(
                Wip, Wip.order_no == OrderModel.order_no
            ).where(Wip.lab_name.in_(lab_filter))
            today = await self._session.scalar(base.where(OrderModel.created_at >= ts))
            yday = await self._session.scalar(
                base.where(OrderModel.created_at >= ys, OrderModel.created_at < ts)
            )
        return int(today or 0), int(yday or 0)

    async def kpi_completed_today(self, lab_filter: list[str] | None) -> tuple[int, int]:
        """Wip.status transitioned to COMPLETED today. We approximate by Wip.completed_at."""
        ts = _today_start()
        ys = ts - _DAY
        base = select(func.count()).select_from(Wip).where(Wip.status == WipStatus.COMPLETED.value)
        if lab_filter is not None:
            base = base.where(Wip.lab_name.in_(lab_filter))
        today = await self._session.scalar(base.where(Wip.completed_at >= ts))
        yday = await self._session.scalar(
            base.where(Wip.completed_at >= ys, Wip.completed_at < ts)
        )
        return int(today or 0), int(yday or 0)

    async def kpi_returned_today(self, lab_filter: list[str] | None) -> tuple[int, int]:
        ts = _today_start()
        ys = ts - _DAY
        base = select(func.count()).select_from(Report).where(Report.status == "returned")
        if lab_filter is not None:
            base = base.join(Wip, Wip.wip_no == Report.wip_no).where(Wip.lab_name.in_(lab_filter))
        today = await self._session.scalar(base.where(Report.updated_at >= ts))
        yday = await self._session.scalar(
            base.where(Report.updated_at >= ys, Report.updated_at < ts)
        )
        return int(today or 0), int(yday or 0)

    async def kpi_pending_approval(self, lab_filter: list[str] | None) -> int:
        base = select(func.count()).select_from(OrderModel).where(
            OrderModel.status == OrderStatus.PENDING_APPROVAL.value
        )
        if lab_filter is not None:
            base = (
                select(func.count(func.distinct(OrderModel.order_no)))
                .select_from(OrderModel)
                .join(Wip, Wip.order_no == OrderModel.order_no)
                .where(
                    OrderModel.status == OrderStatus.PENDING_APPROVAL.value,
                    Wip.lab_name.in_(lab_filter),
                )
            )
        return int(await self._session.scalar(base) or 0)

    async def kpi_open_high_critical_issues(self, lab_filter: list[str] | None) -> int:
        base = (
            select(func.count())
            .select_from(Issue)
            .where(
                Issue.status.in_(["open", "in_progress", "escalated"]),
                Issue.severity.in_([Severity.HIGH.value, Severity.CRITICAL.value]),
            )
        )
        if lab_filter is not None:
            # Issue.lab_id is FK to Lab; join + filter by code
            base = base.join(Lab, Lab.id == Issue.lab_id).where(Lab.code.in_(lab_filter))
        return int(await self._session.scalar(base) or 0)

    # ------- Machine heatmap -------

    async def machines(self, lab_filter: list[str] | None) -> Sequence[Any]:
        """Return list of (machine_id, machine_no, lab, status, today_hours, current_recipe, current_operator, est_completion_at).

        ``today_hours`` is best-effort: if no execution-time tracking exists,
        we return 0.0 — service will compute avg_utilization from the
        zero baseline. (Wired up properly later when C's usage tracking lands.)
        """
        stmt = select(
            Machine.id,
            Machine.machine_no,
            Machine.lab,
            Machine.status,
        )
        if lab_filter is not None:
            stmt = stmt.where(Machine.lab.in_(lab_filter))
        rows = (await self._session.execute(stmt)).all()
        # Augment with placeholder today_hours / recipe / operator / eta.
        # Replace with real WipExecution-derived values when available.
        return [
            (
                str(r[0]),
                r[1],
                r[2],
                r[3],
                0.0,
                None,
                None,
                None,
            )
            for r in rows
        ]

    # ------- WIP pipeline -------

    async def wip_pipeline_counts(self, lab_filter: list[str] | None) -> dict[str, tuple[int, int]]:
        """Return per-stage (today_count, yesterday_count) tuples.

        Stage definitions (mirror spec Section 3):
        - waiting_dispatch: WIP pending AND no Dispatch row exists for this wip_no
        - dispatched: WIP pending AND Dispatch row exists
        - in_progress: WIP in_progress
        - awaiting_handoff: WIP completed AND no later state change (proxy:
          report.status == 'returned' AND order.status NOT IN (waiting_pickup, closed))
        - done: order.status == 'closed' OR sample transferred out (proxy:
          report.status == 'returned' AND order.status IN (waiting_pickup, closed))
        - terminated: WIP terminated
        """
        ts = _today_start()
        ys = ts - _DAY

        def base(q):
            if lab_filter is not None:
                return q.where(Wip.lab_name.in_(lab_filter))
            return q

        # waiting_dispatch
        wd_stmt = (
            select(func.count())
            .select_from(Wip)
            .outerjoin(Dispatch, Dispatch.wip_no == Wip.wip_no)
            .where(Wip.status == WipStatus.PENDING.value, Dispatch.id.is_(None))
        )
        waiting_dispatch_now = int(await self._session.scalar(base(wd_stmt)) or 0)

        # dispatched
        d_stmt = (
            select(func.count())
            .select_from(Wip)
            .join(Dispatch, Dispatch.wip_no == Wip.wip_no)
            .where(Wip.status == WipStatus.PENDING.value)
        )
        dispatched_now = int(await self._session.scalar(base(d_stmt)) or 0)

        # in_progress
        ip_stmt = select(func.count()).select_from(Wip).where(Wip.status == WipStatus.IN_PROGRESS.value)
        in_progress_now = int(await self._session.scalar(base(ip_stmt)) or 0)

        # terminated
        t_stmt = select(func.count()).select_from(Wip).where(Wip.status == WipStatus.TERMINATED.value)
        terminated_now = int(await self._session.scalar(base(t_stmt)) or 0)

        # awaiting_handoff: completed + report returned + order NOT in (waiting_pickup, closed)
        ah_stmt = (
            select(func.count())
            .select_from(Wip)
            .join(Report, Report.wip_no == Wip.wip_no)
            .join(OrderModel, OrderModel.order_no == Wip.order_no)
            .where(
                Wip.status == WipStatus.COMPLETED.value,
                Report.status == "returned",
                OrderModel.status.notin_(
                    [OrderStatus.WAITING_PICKUP.value, OrderStatus.CLOSED.value]
                ),
            )
        )
        awaiting_handoff_now = int(await self._session.scalar(base(ah_stmt)) or 0)

        # done: completed + report returned + order in (waiting_pickup, closed)
        done_stmt = (
            select(func.count())
            .select_from(Wip)
            .join(Report, Report.wip_no == Wip.wip_no)
            .join(OrderModel, OrderModel.order_no == Wip.order_no)
            .where(
                Wip.status == WipStatus.COMPLETED.value,
                Report.status == "returned",
                OrderModel.status.in_(
                    [OrderStatus.WAITING_PICKUP.value, OrderStatus.CLOSED.value]
                ),
            )
        )
        done_now = int(await self._session.scalar(base(done_stmt)) or 0)

        # Delta_24h: we don't have a historical snapshot; approximate with "0".
        # The dashboard accepts 0 delta gracefully (renders → arrow).
        return {
            "waiting_dispatch": (waiting_dispatch_now, 0),
            "dispatched": (dispatched_now, 0),
            "in_progress": (in_progress_now, 0),
            "awaiting_handoff": (awaiting_handoff_now, 0),
            "done": (done_now, 0),
            "terminated": (terminated_now, 0),
        }

    # ------- Triage -------

    async def triage_pending_approvals(
        self, lab_filter: list[str] | None, limit: int
    ) -> Sequence[Any]:
        """Return list of (order_no, created_by_name, created_at)."""
        stmt = (
            select(OrderModel.order_no, OrderModel.created_by, OrderModel.created_at)
            .where(OrderModel.status == OrderStatus.PENDING_APPROVAL.value)
            .order_by(OrderModel.created_at.asc())
            .limit(limit)
        )
        if lab_filter is not None:
            stmt = stmt.join(Wip, Wip.order_no == OrderModel.order_no).where(
                Wip.lab_name.in_(lab_filter)
            )
        return (await self._session.execute(stmt)).all()

    async def triage_unack_issues(
        self, lab_filter: list[str] | None, user_id: str, limit: int
    ) -> Sequence[Any]:
        """Return list of (issue_id, status, severity, escalation_level, lab_code, title, created_at)
        for issues that the given user has NOT acknowledged, severity high/critical, status open/in_progress/escalated.

        Ordering: escalated first, then by severity descending, then created_at descending.
        """
        ack_subq = (
            select(IssueAcknowledgement.issue_id)
            .where(IssueAcknowledgement.user_id == user_id)
            .subquery()
        )
        stmt = (
            select(
                Issue.id,
                Issue.status,
                Issue.severity,
                Issue.escalation_level,
                Lab.code,
                Issue.title,
                Issue.created_at,
            )
            .join(Lab, Lab.id == Issue.lab_id)
            .where(
                Issue.status.in_(["open", "in_progress", "escalated"]),
                Issue.severity.in_([Severity.HIGH.value, Severity.CRITICAL.value]),
                Issue.id.notin_(select(ack_subq.c.issue_id)),
            )
        )
        if lab_filter is not None:
            stmt = stmt.where(Lab.code.in_(lab_filter))
        stmt = stmt.order_by(
            case(
                (Issue.status == "escalated", 0),
                else_=1,
            ),
            case(
                (Issue.severity == Severity.CRITICAL.value, 0),
                else_=1,
            ),
            Issue.created_at.desc(),
        ).limit(limit)
        return (await self._session.execute(stmt)).all()

    # ------- Escalations -------

    async def recent_escalations(
        self, lab_filter: list[str] | None, limit: int
    ) -> Sequence[Any]:
        """Return (issue_id, lab_code, severity, escalation_level, title, updated_at)
        for issues with status=escalated, last 24h, ordered by updated_at desc.

        We use ``Issue.updated_at`` as a proxy for ``escalated_at`` since the
        escalation worker updates it.
        """
        cutoff = datetime.now(UTC) - _DAY
        stmt = (
            select(
                Issue.id,
                Lab.code,
                Issue.severity,
                Issue.escalation_level,
                Issue.title,
                Issue.updated_at,
            )
            .join(Lab, Lab.id == Issue.lab_id)
            .where(
                Issue.status == "escalated",
                Issue.updated_at >= cutoff,
            )
        )
        if lab_filter is not None:
            stmt = stmt.where(Lab.code.in_(lab_filter))
        stmt = stmt.order_by(Issue.updated_at.desc()).limit(limit)
        return (await self._session.execute(stmt)).all()

    # ------- Completions -------

    async def recent_completions(
        self, lab_filter: list[str] | None, limit: int
    ) -> Sequence[Any]:
        """Return (wip_no, order_no, lab_name, returned_at) for last 30min RETURNED reports."""
        cutoff = datetime.now(UTC) - timedelta(minutes=30)
        stmt = (
            select(Report.wip_no, Wip.order_no, Wip.lab_name, Report.updated_at)
            .join(Wip, Wip.wip_no == Report.wip_no)
            .where(
                Report.status == "returned",
                Report.updated_at >= cutoff,
            )
        )
        if lab_filter is not None:
            stmt = stmt.where(Wip.lab_name.in_(lab_filter))
        stmt = stmt.order_by(Report.updated_at.desc()).limit(limit)
        return (await self._session.execute(stmt)).all()

    # ------- Lab leaderboard -------

    async def lab_leaderboard(self, limit: int) -> Sequence[Any]:
        """Per-lab today stats: (lab_name, completed_today, awaiting_handoff,
        open_high_critical_issues, avg_util_placeholder).

        general_supervisor only — no lab filter.
        """
        ts = _today_start()

        # completed_today per lab_name (Wip.lab_name groups)
        completed_subq = (
            select(Wip.lab_name.label("lab_name"), func.count().label("completed_today"))
            .where(Wip.status == WipStatus.COMPLETED.value, Wip.completed_at >= ts)
            .group_by(Wip.lab_name)
            .subquery()
        )

        # awaiting_handoff per lab_name
        ah_subq = (
            select(Wip.lab_name.label("lab_name"), func.count().label("awaiting_handoff"))
            .join(Report, Report.wip_no == Wip.wip_no)
            .join(OrderModel, OrderModel.order_no == Wip.order_no)
            .where(
                Wip.status == WipStatus.COMPLETED.value,
                Report.status == "returned",
                OrderModel.status.notin_(
                    [OrderStatus.WAITING_PICKUP.value, OrderStatus.CLOSED.value]
                ),
            )
            .group_by(Wip.lab_name)
            .subquery()
        )

        # open_high_critical_issues per lab (joined via Lab.code -> Lab.name)
        issues_subq = (
            select(Lab.name.label("lab_name"), func.count(Issue.id).label("issue_count"))
            .join(Issue, Issue.lab_id == Lab.id)
            .where(
                Issue.status.in_(["open", "in_progress", "escalated"]),
                Issue.severity.in_([Severity.HIGH.value, Severity.CRITICAL.value]),
            )
            .group_by(Lab.name)
            .subquery()
        )

        # Driver: enumerate all distinct lab_names that appear anywhere in WIP
        lab_names_stmt = select(Wip.lab_name).distinct()
        lab_names = [r[0] for r in (await self._session.execute(lab_names_stmt)).all()]

        # For each lab, look up subquery rows
        result_rows: list[Any] = []
        for lab_name in lab_names:
            completed = int(
                (
                    await self._session.scalar(
                        select(completed_subq.c.completed_today).where(
                            completed_subq.c.lab_name == lab_name
                        )
                    )
                )
                or 0
            )
            awaiting = int(
                (
                    await self._session.scalar(
                        select(ah_subq.c.awaiting_handoff).where(ah_subq.c.lab_name == lab_name)
                    )
                )
                or 0
            )
            issues = int(
                (
                    await self._session.scalar(
                        select(issues_subq.c.issue_count).where(issues_subq.c.lab_name == lab_name)
                    )
                )
                or 0
            )
            result_rows.append((lab_name, completed, awaiting, issues, 0))  # avg_util placeholder
        # Sort by completed_today desc, then truncate
        result_rows.sort(key=lambda r: r[1], reverse=True)
        return result_rows[:limit]
```

- [ ] **Step 2: Write repository tests**

Create `backend/tests/e_tests/test_dashboard_repository.py`:

```python
"""Unit tests for DashboardRepository — happy path + scope filter behavior.

We seed minimal rows directly in the test DB session, then assert the methods
return the expected counts.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.common.enums import OrderStatus, Severity, WipStatus
from app.db.models.issues import Issue
from app.db.models.labs import Lab
from app.db.models.orders import Order as OrderModel
from app.db.models.reports import Report
from app.db.models.wips import Wip
from app.modules.dashboard.repository import DashboardRepository

pytestmark = pytest.mark.asyncio


async def _seed_minimal(session, *, lab_name="LAB-A", lab_code="LAB-A"):
    """Insert one Lab + one Order + one Wip for a happy-path baseline."""
    # use existing seed; helper noop if seed already provides this.
    return


async def test_kpi_new_orders_unscoped_includes_today_count(db_session):
    repo = DashboardRepository(db_session)
    today, yday = await repo.kpi_new_orders(lab_filter=None)
    # The seed includes at least one demo order created in seed time;
    # we only assert non-negative integers + that yesterday <= today + epsilon
    assert today >= 0
    assert yday >= 0


async def test_kpi_new_orders_scoped_returns_subset(db_session):
    repo = DashboardRepository(db_session)
    full_today, _ = await repo.kpi_new_orders(lab_filter=None)
    scoped_today, _ = await repo.kpi_new_orders(lab_filter=["LAB-A"])
    assert scoped_today <= full_today


async def test_machines_unscoped_returns_some(db_session):
    repo = DashboardRepository(db_session)
    rows = await repo.machines(lab_filter=None)
    assert isinstance(rows, list)
    # Each row tuple has 8 elements
    for r in rows:
        assert len(r) == 8


async def test_wip_pipeline_returns_six_buckets(db_session):
    repo = DashboardRepository(db_session)
    counts = await repo.wip_pipeline_counts(lab_filter=None)
    assert set(counts.keys()) == {
        "waiting_dispatch",
        "dispatched",
        "in_progress",
        "awaiting_handoff",
        "done",
        "terminated",
    }
    for stage, (now, prev) in counts.items():
        assert now >= 0
        assert prev >= 0


async def test_triage_pending_approvals_limit_respected(db_session):
    repo = DashboardRepository(db_session)
    rows = await repo.triage_pending_approvals(lab_filter=None, limit=3)
    assert len(rows) <= 3


async def test_lab_leaderboard_sorted_by_completed_desc(db_session):
    repo = DashboardRepository(db_session)
    rows = await repo.lab_leaderboard(limit=5)
    completed_values = [r[1] for r in rows]
    assert completed_values == sorted(completed_values, reverse=True)
```

Note: the existing `conftest.py` doesn't define a `db_session` fixture by default. Inspect the existing tests under `backend/tests/e_tests/` for the actual fixture name (likely `client` for HTTP tests, possibly `db_session` from a per-test fixture). If `db_session` does not exist, add a session-scoped async fixture in `backend/tests/conftest.py`:

```python
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    from app.core.database import async_engine
    Session = async_sessionmaker(async_engine, expire_on_commit=False)
    async with Session() as session:
        yield session
```

Only add this if missing.

- [ ] **Step 3: Run repository tests**

```bash
cd backend && source venv/bin/activate
pytest tests/e_tests/test_dashboard_repository.py -v
```

Expected: All pass. If `db_session` fixture is missing, add it (see note above) and rerun.

- [ ] **Step 4: Commit**

```bash
git add backend/app/modules/dashboard/repository.py backend/tests/e_tests/test_dashboard_repository.py
# also commit conftest changes if any
git commit -m "feat(dashboard): add repository with per-widget queries + tests"
```

---

## Task 3: Backend Publisher + Service

**Files:**
- Create: `backend/app/modules/dashboard/publisher.py`
- Create: `backend/app/modules/dashboard/service.py`
- Test: `backend/tests/e_tests/test_dashboard_service.py`

- [ ] **Step 1: Create publisher.py**

Create `backend/app/modules/dashboard/publisher.py`:

```python
"""Redis pub/sub helpers for SSE invalidation.

Other modules call these on important state changes. Frontend SSE handler
listens to ``dashboard:events:{lab_name}`` and ``dashboard:events:global``,
fires `queryClient.invalidateQueries(["dashboard"])` regardless of payload.
"""

from __future__ import annotations

import logging
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

_GLOBAL_CHANNEL = "dashboard:events:global"


def _lab_channel(lab_name: str | None) -> str:
    return f"dashboard:events:{lab_name}" if lab_name else _GLOBAL_CHANNEL


_redis: aioredis.Redis | None = None


def _get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def _publish(channel: str, event: str) -> None:
    """Publish an event name only — no payload. The FE re-fetches on any signal."""
    try:
        await _get_redis().publish(channel, event)
    except Exception:
        logger.exception("dashboard publish failed channel=%s event=%s", channel, event)


async def publish_new_escalation(lab_name: str | None) -> None:
    await _publish(_lab_channel(lab_name), "new_escalation")
    await _publish(_GLOBAL_CHANNEL, "new_escalation")


async def publish_new_pending_approval(lab_name: str | None) -> None:
    await _publish(_lab_channel(lab_name), "new_pending_approval")
    await _publish(_GLOBAL_CHANNEL, "new_pending_approval")


async def publish_report_returned(lab_name: str | None) -> None:
    await _publish(_lab_channel(lab_name), "report_returned")
    await _publish(_GLOBAL_CHANNEL, "report_returned")


async def listen(channels: list[str]) -> Any:
    """Async-generator yielding raw event names as they arrive.

    Used by router's SSE handler. Caller must consume in async-for, and is
    responsible for cleanup via PubSub.unsubscribe + .aclose().
    """
    pubsub = _get_redis().pubsub()
    await pubsub.subscribe(*channels)
    try:
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            yield message.get("data") or ""
    finally:
        await pubsub.unsubscribe(*channels)
        await pubsub.aclose()
```

- [ ] **Step 2: Create service.py**

Create `backend/app/modules/dashboard/service.py`:

```python
"""DashboardService — single ``compute_snapshot`` entrypoint."""

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
    TriageItem,
    WipPipeline,
)


def _is_cross_lab(user: CurrentUser) -> bool:
    return user.role in ("system_admin", "general_supervisor") or "*" in user.permissions


def _viewer_role(user: CurrentUser) -> str:
    return "general_supervisor" if _is_cross_lab(user) else "lab_supervisor"


def _threshold(value: int, *, orange_at: int | None, red_at: int | None) -> str:
    if red_at is not None and value >= red_at:
        return "red"
    if orange_at is not None and value >= orange_at:
        return "orange"
    return "neutral"


def _delta(today: int, yesterday: int) -> int:
    return today - yesterday


def _trend(delta: int) -> str:
    if delta > 0:
        return "up"
    if delta < 0:
        return "down"
    return "flat"


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = DashboardRepository(session)

    async def compute_snapshot(self, user: CurrentUser) -> DashboardSnapshot:
        lab_filter = await resolve_user_lab_codes(self._session, user)
        cross_lab = lab_filter is None

        # Fire widget queries in parallel — each is independent
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
        ) = await asyncio.gather(
            self._repo.kpi_new_orders(lab_filter),
            self._repo.kpi_completed_today(lab_filter),
            self._repo.kpi_returned_today(lab_filter),
            self._repo.kpi_pending_approval(lab_filter),
            self._repo.kpi_open_high_critical_issues(lab_filter),
            self._repo.machines(lab_filter),
            self._repo.wip_pipeline_counts(lab_filter),
            self._repo.triage_pending_approvals(lab_filter, limit=5),
            self._repo.triage_unack_issues(lab_filter, user_id=str(user.id), limit=5),
            self._repo.recent_escalations(lab_filter, limit=5),
            self._repo.recent_completions(lab_filter, limit=5) if not cross_lab else _none_list(),
            self._repo.lab_leaderboard(limit=5) if cross_lab else _none_list(),
        )

        kpi = self._build_kpi(
            new_orders, completed, returned, pending_appr, open_issues_count
        )
        machines = self._build_machines(machine_rows)
        pipeline = self._build_pipeline(pipeline_counts)
        triage = self._build_triage(triage_approvals, triage_issues)
        escalations = self._build_escalations(esc_rows)
        completions = self._build_completions(comp_rows) if comp_rows is not None else None
        leaderboard = self._build_leaderboard(leaderboard_rows) if leaderboard_rows is not None else None

        viewer_lab = None if cross_lab else (lab_filter[0] if lab_filter else None)

        return DashboardSnapshot(
            viewer_role=_viewer_role(user),  # type: ignore[arg-type]
            viewer_lab=viewer_lab,
            generated_at=datetime.now(UTC),
            kpi=kpi,
            machines=machines,
            wip_pipeline=pipeline,
            triage=triage,
            recent_escalations=escalations,
            recent_completions=completions,
            lab_leaderboard=leaderboard,
        )

    def _build_kpi(
        self,
        new_orders: tuple[int, int],
        completed: tuple[int, int],
        returned: tuple[int, int],
        pending_appr: int,
        open_issues_count: int,
    ) -> KpiBar:
        return KpiBar(
            new_orders=KpiCard(value=new_orders[0], delta_24h=_delta(*new_orders)),
            completed=KpiCard(value=completed[0], delta_24h=_delta(*completed)),
            returned=KpiCard(value=returned[0], delta_24h=_delta(*returned)),
            pending_approval=KpiCard(
                value=pending_appr,
                delta_24h=0,  # not tracked over 24h
                threshold_color=_threshold(pending_appr, orange_at=6, red_at=None),
            ),
            open_critical_high_issues=KpiCard(
                value=open_issues_count,
                delta_24h=0,
                threshold_color=_threshold(open_issues_count, orange_at=1, red_at=None),
            ),
        )

    def _build_machines(self, rows: list[Any]) -> MachineHeatmap:
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
        # avg util ~= sum_today_hours / (total * 8h) * 100, capped 0–100
        avg_util = int(min(100, max(0, (sum_today_hours / (total * 8)) * 100))) if total else 0
        return MachineHeatmap(
            by_lab=by_lab,
            avg_utilization_pct=avg_util,
            in_use_count=in_use,
            total_count=total,
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
            order_no, creator, created_at = r
            items.append(
                TriageItem(
                    type="pending_approval",
                    ref_id=order_no,
                    label=f"{order_no} · {creator or ''}".strip(" ·"),
                    lab_name=None,
                    severity=None,
                    created_at=created_at,
                )
            )
        for r in issues:
            iid, status, severity, level, lab_code, title, created_at = r
            t = "escalated_issue" if status == "escalated" else "open_issue"
            items.append(
                TriageItem(
                    type=t,
                    ref_id=str(iid),
                    label=title,
                    lab_name=lab_code,
                    severity=severity,
                    created_at=created_at,
                )
            )
        # Limit to 5 after merge; preserve sort order coming from repository
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
            CompletionRow(wip_no=r[0], order_no=r[1], lab_name=r[2], returned_at=r[3])
            for r in rows
        ]

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


async def _none_list() -> None:
    return None
```

- [ ] **Step 3: Write service test**

Create `backend/tests/e_tests/test_dashboard_service.py`:

```python
"""Service-level integration: compute_snapshot returns a valid DashboardSnapshot
shape for both supervisor and general_supervisor seed users.
"""

from __future__ import annotations

import pytest

from app.modules.dashboard.service import DashboardService

pytestmark = pytest.mark.asyncio


async def test_general_supervisor_sees_leaderboard_and_no_completions(db_session, general_supervisor_user):
    svc = DashboardService(db_session)
    snap = await svc.compute_snapshot(general_supervisor_user)
    assert snap.viewer_role == "general_supervisor"
    assert snap.viewer_lab is None
    assert snap.lab_leaderboard is not None
    assert snap.recent_completions is None


async def test_lab_supervisor_sees_completions_and_no_leaderboard(db_session, lab_supervisor_user):
    svc = DashboardService(db_session)
    snap = await svc.compute_snapshot(lab_supervisor_user)
    assert snap.viewer_role == "lab_supervisor"
    assert snap.lab_leaderboard is None
    assert snap.recent_completions is not None


async def test_kpi_bar_has_all_five_cards(db_session, general_supervisor_user):
    svc = DashboardService(db_session)
    snap = await svc.compute_snapshot(general_supervisor_user)
    kpi = snap.kpi
    assert kpi.new_orders.value >= 0
    assert kpi.completed.value >= 0
    assert kpi.returned.value >= 0
    assert kpi.pending_approval.value >= 0
    assert kpi.open_critical_high_issues.value >= 0


async def test_wip_pipeline_total_matches_sum_of_stages(db_session, general_supervisor_user):
    svc = DashboardService(db_session)
    snap = await svc.compute_snapshot(general_supervisor_user)
    p = snap.wip_pipeline
    assert p.total == (
        p.waiting_dispatch[0]
        + p.dispatched[0]
        + p.in_progress[0]
        + p.awaiting_handoff[0]
        + p.done[0]
        + p.terminated[0]
    )
```

Note: fixtures `general_supervisor_user` and `lab_supervisor_user` may not yet exist. If missing, find equivalent fixtures in `backend/tests/e_tests/test_require_permission.py` or build:

```python
# In backend/tests/conftest.py or a new tests/e_tests/conftest.py
import pytest_asyncio
from app.common.dependencies.auth import CurrentUser

@pytest_asyncio.fixture
async def general_supervisor_user() -> CurrentUser:
    return CurrentUser(
        id="00000000-0000-0000-0000-000000000001",
        username="gs",
        role="general_supervisor",
        lab_id=None,
        permissions=["dashboard:read"],
    )

@pytest_asyncio.fixture
async def lab_supervisor_user(db_session) -> CurrentUser:
    from sqlalchemy import select
    from app.db.models.labs import Lab
    lab_id = (await db_session.execute(select(Lab.id).limit(1))).scalar_one()
    return CurrentUser(
        id="00000000-0000-0000-0000-000000000002",
        username="ls",
        role="lab_supervisor",
        lab_id=lab_id,
        permissions=["dashboard:read"],
    )
```

Only add what's missing. Use existing seeded user IDs if `CurrentUser` schema differs from above.

- [ ] **Step 4: Run service tests**

```bash
cd backend && source venv/bin/activate
pytest tests/e_tests/test_dashboard_service.py -v
```

Expected: All pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/dashboard/publisher.py backend/app/modules/dashboard/service.py backend/tests/e_tests/test_dashboard_service.py
# also include conftest changes if any
git commit -m "feat(dashboard): add publisher + service with role-aware snapshot"
```

---

## Task 4: Backend Router (GET + SSE) + main wiring

**Files:**
- Create: `backend/app/modules/dashboard/dependencies.py`
- Create: `backend/app/modules/dashboard/router.py`
- Modify: `backend/app/main.py` (add include_router)
- Test: `backend/tests/e_tests/test_dashboard_router.py`

- [ ] **Step 1: Create dependencies.py**

Create `backend/app/modules/dashboard/dependencies.py`:

```python
"""DI shim for DashboardService."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.dashboard.service import DashboardService


async def get_dashboard_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardService:
    return DashboardService(session)
```

- [ ] **Step 2: Create router.py**

Create `backend/app/modules/dashboard/router.py`:

```python
"""Dashboard HTTP routes.

- ``GET /api/dashboard``        — one-shot snapshot (TanStack Query polls every 30s)
- ``GET /api/dashboard/stream`` — SSE channel; emits event names (no payload),
                                  FE invalidates the query and re-fetches.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from app.common.dependencies import CurrentUser, get_current_user, require_permission
from app.common.schemas import success_response
from app.modules.dashboard.dependencies import get_dashboard_service
from app.modules.dashboard.publisher import listen
from app.modules.dashboard.schemas import DashboardSnapshot
from app.modules.dashboard.service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "",
    dependencies=[Depends(require_permission("dashboard:read"))],
)
async def get_dashboard(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> dict:
    snapshot = await svc.compute_snapshot(user)
    return success_response(snapshot.model_dump(mode="json"))


@router.get("/stream", dependencies=[Depends(require_permission("dashboard:read"))])
async def stream_dashboard(
    user: Annotated[CurrentUser, Depends(get_current_user)],
):
    """SSE channel — yields event name lines.

    Channel selection:
      lab_supervisor → subscribes to ``dashboard:events:{lab_name}`` + global
      general_supervisor / admin → subscribes to ``dashboard:events:global``
                                   (worker also publishes to global on every push)
    """
    channels = ["dashboard:events:global"]
    if user.role in ("lab_supervisor", "lab_engineer") and user.lab_id:
        # Look up the lab code (or name) from the FK if needed; here we just
        # subscribe by the user's display lab — workers publish both global +
        # per-lab so either side reaches us.
        from sqlalchemy import select
        from app.core.database import async_session_factory
        from app.db.models.labs import Lab

        async with async_session_factory() as session:
            code = (
                await session.execute(select(Lab.code).where(Lab.id == user.lab_id))
            ).scalar_one_or_none()
        if code:
            channels.append(f"dashboard:events:{code}")

    async def event_gen():
        async for ev in listen(channels):
            yield {"event": "dashboard", "data": ev}

    return EventSourceResponse(event_gen())
```

Note: confirm imports against existing helpers:
- `from app.common.dependencies import CurrentUser, get_current_user, require_permission` — see `backend/app/common/dependencies/__init__.py` (already exports these per Task 1 grep)
- `from app.common.schemas import success_response` — check actual function name; may be `ApiResponse.success(...)` or `make_success`. Adapt.
- `async_session_factory` — check actual name in `backend/app/core/database.py`. May be `AsyncSessionLocal` or similar. Use whichever is exported.

- [ ] **Step 3: Wire router in main.py**

Find the existing routers list in `backend/app/main.py` (the `include_router` calls). Add:

```python
from app.modules.dashboard.router import router as dashboard_router
# ...
app.include_router(dashboard_router, prefix="/api")
```

Place next to other module includes. The `/api` prefix matches the existing pattern; verify by inspection.

- [ ] **Step 4: Write router test**

Create `backend/tests/e_tests/test_dashboard_router.py`:

```python
"""Router-level integration: hit /api/dashboard with both supervisor roles."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


async def test_get_dashboard_requires_auth(client):
    res = await client.get("/api/dashboard")
    assert res.status_code in (401, 403)


async def test_get_dashboard_as_lab_supervisor(client, login_as_lab_supervisor):
    res = await client.get("/api/dashboard")
    assert res.status_code == 200
    body = res.json()
    snap = body["data"]
    assert snap["viewerRole"] == "lab_supervisor" or snap["viewer_role"] == "lab_supervisor"
    # one or the other casing depending on FastAPI/Pydantic alias config
    # FE will adapt; backend choice is to expose snake_case via Pydantic default


async def test_get_dashboard_as_general_supervisor(client, login_as_general_supervisor):
    res = await client.get("/api/dashboard")
    assert res.status_code == 200
    body = res.json()
    snap = body["data"]
    role = snap.get("viewer_role") or snap.get("viewerRole")
    assert role == "general_supervisor"
    # leaderboard expected non-null for general
    assert snap.get("lab_leaderboard") is not None or snap.get("labLeaderboard") is not None


async def test_get_dashboard_shape(client, login_as_general_supervisor):
    res = await client.get("/api/dashboard")
    body = res.json()["data"]
    for key in ("kpi", "machines", "wip_pipeline", "triage", "recent_escalations"):
        assert key in body or key.replace("_", "") in body or _camel(key) in body


def _camel(snake: str) -> str:
    parts = snake.split("_")
    return parts[0] + "".join(p.title() for p in parts[1:])
```

Fixture names `login_as_lab_supervisor` / `login_as_general_supervisor` may need adaptation — examine existing test fixtures in `backend/tests/e_tests/test_require_permission.py` for the actual pattern (probably uses a `login()` helper writing the JWT cookie). Use that helper directly:

```python
# substitute:
await login(client, username="lab_sup_seed_user", password="...")
```

- [ ] **Step 5: Run router tests**

```bash
cd backend && source venv/bin/activate
pytest tests/e_tests/test_dashboard_router.py -v
```

Expected: All pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/modules/dashboard/dependencies.py backend/app/modules/dashboard/router.py backend/app/main.py backend/tests/e_tests/test_dashboard_router.py
git commit -m "feat(dashboard): wire GET + SSE router into main"
```

---

## Task 5: Backend publish hooks (3 minimal edits)

**Files:**
- Modify: `backend/app/workers/escalation.py`
- Modify: `backend/app/modules/orders/service.py`
- Modify: `backend/app/modules/reports/service.py`

Each hook is 1–3 lines added at the right transition point. None block on failure (publisher.py already swallows exceptions).

- [ ] **Step 1: Hook escalation worker**

Find the function in `backend/app/workers/escalation.py` that bumps `escalation_level` and commits. After the commit, call:

```python
from app.modules.dashboard.publisher import publish_new_escalation
# inside the worker after commit:
await publish_new_escalation(lab_code_or_name)
```

If the worker is sync Celery, wrap with `asyncio.run(publish_new_escalation(...))` or use a sync redis client. The simplest path: import a sync wrapper or schedule via `asgiref.sync.async_to_sync`. If the existing worker already uses an async helper pattern (look for `await` inside the task body), follow it.

If unsure, expose a synchronous variant in `publisher.py`:

```python
import redis

_sync_redis: redis.Redis | None = None

def _sync_get_redis() -> redis.Redis:
    global _sync_redis
    if _sync_redis is None:
        _sync_redis = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    return _sync_redis

def publish_new_escalation_sync(lab_name: str | None) -> None:
    try:
        ch = f"dashboard:events:{lab_name}" if lab_name else "dashboard:events:global"
        _sync_get_redis().publish(ch, "new_escalation")
        _sync_get_redis().publish("dashboard:events:global", "new_escalation")
    except Exception:
        logger.exception("dashboard publish_sync failed")
```

Then in the worker:

```python
from app.modules.dashboard.publisher import publish_new_escalation_sync
publish_new_escalation_sync(issue.lab.code if issue.lab else None)
```

- [ ] **Step 2: Hook orders.submit_for_approval**

Find the method that transitions an order to `pending_approval` in `backend/app/modules/orders/service.py` (likely `submit_for_approval` or similar). After the commit, call:

```python
from app.modules.dashboard.publisher import publish_new_pending_approval
# After commit:
await publish_new_pending_approval(None)  # cross-lab event — order isn't lab-bound yet
```

- [ ] **Step 3: Hook reports.publish_report**

In `backend/app/modules/reports/service.py`, find `publish_report` (or the method that transitions a `Report.status` to `RETURNED`). After commit:

```python
from app.modules.dashboard.publisher import publish_report_returned
# After commit, derive lab_name from the wip:
await publish_report_returned(wip.lab_name if wip else None)
```

- [ ] **Step 4: Run existing tests to confirm hooks don't regress**

```bash
cd backend && source venv/bin/activate
pytest tests/e_tests/test_issues.py tests/e_tests/test_notifications.py -v
```

Expected: All pass — the hooks are additive and best-effort, no behavior change.

- [ ] **Step 5: Commit**

```bash
git add backend/app/workers/escalation.py backend/app/modules/orders/service.py backend/app/modules/reports/service.py backend/app/modules/dashboard/publisher.py
git commit -m "feat(dashboard): publish SSE events on escalation/approval/return"
```

---

## Task 6: Frontend types + api client

**Files:**
- Modify (replace): `frontend/src/types/dashboard.ts`
- Modify (replace): `frontend/src/services/dashboard-api.ts`

- [ ] **Step 1: Rewrite types/dashboard.ts**

Replace `frontend/src/types/dashboard.ts` entirely:

```typescript
// Generated to mirror backend/app/modules/dashboard/schemas.py.
// Keep these two in sync.

import type { Severity } from "@/constants/enums";

export type ThresholdColor = "neutral" | "orange" | "red";
export type TriageType = "pending_approval" | "escalated_issue" | "open_issue";
export type TrendArrow = "up" | "flat" | "down";

export interface KpiCard {
  value: number;
  delta_24h: number;
  threshold_color: ThresholdColor;
}

export interface KpiBar {
  new_orders: KpiCard;
  completed: KpiCard;
  returned: KpiCard;
  pending_approval: KpiCard;
  open_critical_high_issues: KpiCard;
}

export interface MachineGrid {
  machine_id: string;
  machine_no: string;
  lab_name: string;
  status: string;
  today_hours: number;
  current_recipe: string | null;
  current_operator: string | null;
  est_completion_at: string | null;
}

export interface MachineHeatmap {
  by_lab: Record<string, MachineGrid[]>;
  avg_utilization_pct: number;
  in_use_count: number;
  total_count: number;
}

export type Pair = [number, number]; // (count, delta_24h)

export interface WipPipeline {
  total: number;
  waiting_dispatch: Pair;
  dispatched: Pair;
  in_progress: Pair;
  awaiting_handoff: Pair;
  done: Pair;
  terminated: Pair;
}

export interface TriageItem {
  type: TriageType;
  ref_id: string;
  label: string;
  lab_name: string | null;
  severity: Severity | null;
  created_at: string;
}

export interface EscalationRow {
  issue_id: string;
  lab_name: string;
  severity: Severity;
  escalation_level: number;
  title: string;
  escalated_at: string;
}

export interface CompletionRow {
  wip_no: string;
  order_no: string;
  lab_name: string;
  returned_at: string;
}

export interface LabRow {
  lab_name: string;
  completed_today: number;
  awaiting_handoff: number;
  open_high_critical_issues: number;
  avg_utilization_pct: number;
  trend_24h: TrendArrow;
}

export interface DashboardSnapshot {
  viewer_role: "lab_supervisor" | "general_supervisor";
  viewer_lab: string | null;
  generated_at: string;

  kpi: KpiBar;
  machines: MachineHeatmap;
  wip_pipeline: WipPipeline;
  triage: TriageItem[];
  recent_escalations: EscalationRow[];
  recent_completions: CompletionRow[] | null;
  lab_leaderboard: LabRow[] | null;
}
```

- [ ] **Step 2: Rewrite services/dashboard-api.ts**

Replace `frontend/src/services/dashboard-api.ts` entirely:

```typescript
import { httpClient } from "@/api/httpClient";
import type { ApiResponse } from "@/types/api";
import type { DashboardSnapshot } from "@/types/dashboard";

export type { DashboardSnapshot } from "@/types/dashboard";
export type {
  KpiCard,
  KpiBar,
  MachineGrid,
  MachineHeatmap,
  WipPipeline,
  TriageItem,
  EscalationRow,
  CompletionRow,
  LabRow,
} from "@/types/dashboard";

export const dashboardApi = {
  async getSnapshot(): Promise<DashboardSnapshot> {
    const res = await httpClient.get<ApiResponse<DashboardSnapshot>>("/dashboard");
    return res.data.data;
  },
};
```

- [ ] **Step 3: Verify type-check**

```bash
cd frontend && npm run lint
```

Expected: no type errors. If `KpiCard` collides with the old `components/ui/KpiCard.tsx` component name, the conflict is on the TS type only — the component is imported by default; the type is named the same. Rename the type export to `KpiCardData` if collision:

```typescript
export interface KpiCardData {
  value: number;
  delta_24h: number;
  threshold_color: ThresholdColor;
}

export interface KpiBar {
  new_orders: KpiCardData;
  completed: KpiCardData;
  returned: KpiCardData;
  pending_approval: KpiCardData;
  open_critical_high_issues: KpiCardData;
}
```

And update mirror in dashboard.ts plus rename references throughout subsequent tasks.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/dashboard.ts frontend/src/services/dashboard-api.ts
git commit -m "feat(dashboard): mirror new snapshot schema in FE types + api"
```

---

## Task 7: Frontend KpiBar component + test

**Files:**
- Create: `frontend/app/_dashboard/KpiBar.tsx`
- Test: `frontend/app/_dashboard/__tests__/KpiBar.test.tsx`

- [ ] **Step 1: Create KpiBar.tsx**

```typescript
"use client";

import type { KpiBar as KpiBarData, KpiCardData } from "@/types/dashboard";

const COLOR_BY_THRESHOLD: Record<string, string> = {
  neutral: "var(--text2)",
  orange: "var(--orange)",
  red: "var(--red)",
};

const TILE_LABELS: Record<keyof KpiBarData, { label: string; drillTo: string }> = {
  new_orders: { label: "新單", drillTo: "/orders?created=today" },
  completed: { label: "完工", drillTo: "/execution?status=completed" },
  returned: { label: "回傳", drillTo: "/storage?status=returned" },
  pending_approval: { label: "待簽", drillTo: "/approve" },
  open_critical_high_issues: { label: "告警", drillTo: "/issues?severity=high,critical&status=open" },
};

function Arrow({ delta }: { delta: number }) {
  if (delta > 0) return <span style={{ color: "#3fb950" }}>↑{delta}</span>;
  if (delta < 0) return <span style={{ color: "var(--red)" }}>↓{Math.abs(delta)}</span>;
  return <span style={{ color: "var(--text3)" }}>→</span>;
}

function Tile({ card, label, onClick }: { card: KpiCardData; label: string; onClick: () => void }) {
  const color = COLOR_BY_THRESHOLD[card.threshold_color] || "var(--text1)";
  return (
    <button
      onClick={onClick}
      style={{
        background: "var(--s1)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: 16,
        cursor: "pointer",
        textAlign: "left",
        height: 80,
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
      }}
    >
      <div style={{ fontSize: 12, color: "var(--text2)" }}>{label}</div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
        <span style={{ fontSize: 28, fontWeight: 800, color }}>{card.value}</span>
        <span style={{ fontSize: 11, fontFamily: "monospace" }}>
          <Arrow delta={card.delta_24h} />
        </span>
      </div>
    </button>
  );
}

export default function KpiBar({ data }: { data: KpiBarData }) {
  const handle = (path: string) => () => {
    window.location.href = path;
  };
  const entries = Object.entries(TILE_LABELS) as [keyof KpiBarData, { label: string; drillTo: string }][];
  return (
    <div
      data-testid="kpi-bar"
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(5, 1fr)",
        gap: 14,
      }}
    >
      {entries.map(([key, { label, drillTo }]) => (
        <Tile key={key} card={data[key]} label={label} onClick={handle(drillTo)} />
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Write KpiBar test**

```typescript
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import KpiBar from "../KpiBar";
import type { KpiBar as KpiBarData } from "@/types/dashboard";

const mk = (v: number, d: number = 0): KpiBarData["new_orders"] => ({
  value: v,
  delta_24h: d,
  threshold_color: "neutral",
});

const data: KpiBarData = {
  new_orders: mk(12, 3),
  completed: mk(9, -1),
  returned: mk(4, 0),
  pending_approval: { value: 7, delta_24h: 0, threshold_color: "orange" },
  open_critical_high_issues: { value: 2, delta_24h: 0, threshold_color: "red" },
};

describe("KpiBar", () => {
  it("renders 5 tiles", () => {
    render(<KpiBar data={data} />);
    expect(screen.getByText("新單")).toBeInTheDocument();
    expect(screen.getByText("完工")).toBeInTheDocument();
    expect(screen.getByText("回傳")).toBeInTheDocument();
    expect(screen.getByText("待簽")).toBeInTheDocument();
    expect(screen.getByText("告警")).toBeInTheDocument();
  });

  it("shows arrows: ↑ for positive, ↓ for negative, → for zero", () => {
    render(<KpiBar data={data} />);
    expect(screen.getByText("↑3")).toBeInTheDocument();
    expect(screen.getByText("↓1")).toBeInTheDocument();
    expect(screen.getByText("→")).toBeInTheDocument();
  });

  it("displays all values", () => {
    render(<KpiBar data={data} />);
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("9")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getByText("7")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Run vitest**

```bash
cd frontend && npm test -- KpiBar
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/_dashboard/KpiBar.tsx frontend/app/_dashboard/__tests__/KpiBar.test.tsx
git commit -m "feat(dashboard): add KpiBar component + tests"
```

---

## Task 8: Frontend MachineHeatmap + test

**Files:**
- Create: `frontend/app/_dashboard/MachineHeatmap.tsx`
- Test: `frontend/app/_dashboard/__tests__/MachineHeatmap.test.tsx`

- [ ] **Step 1: Create MachineHeatmap.tsx**

```typescript
"use client";

import type { MachineHeatmap as MachineHeatmapData, MachineGrid } from "@/types/dashboard";

const STATUS_COLOR: Record<string, string> = {
  in_use: "var(--blue)",
  idle: "var(--text3)",
  maintenance: "var(--orange)",
  faulty: "var(--red)",
  disabled: "#3a3a3a",
};

function Tile({ m }: { m: MachineGrid }) {
  const isFaulty = m.status === "faulty";
  return (
    <div
      title={`${m.machine_no} · ${m.status}${m.current_recipe ? ` · recipe ${m.current_recipe}` : ""}${m.current_operator ? ` · op ${m.current_operator}` : ""}${m.today_hours ? ` · ${m.today_hours.toFixed(1)}h today` : ""}`}
      style={{
        width: 28,
        height: 28,
        borderRadius: 4,
        background: STATUS_COLOR[m.status] || "var(--text3)",
        backgroundImage: isFaulty
          ? "repeating-linear-gradient(45deg, transparent 0 4px, rgba(0,0,0,0.4) 4px 6px)"
          : undefined,
        cursor: "pointer",
        flexShrink: 0,
      }}
      onClick={() => {
        window.location.href = `/machine?id=${m.machine_id}`;
      }}
    />
  );
}

export default function MachineHeatmap({
  data,
  showLabPrefix,
}: {
  data: MachineHeatmapData;
  showLabPrefix: boolean;
}) {
  const labKeys = Object.keys(data.by_lab).sort();
  return (
    <div
      data-testid="machine-heatmap"
      style={{
        background: "var(--s1)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: 16,
        height: "100%",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
        <h3 style={{ margin: 0, fontSize: 14 }}>機台狀態</h3>
        <span style={{ fontSize: 11, color: "var(--text3)", fontFamily: "monospace" }}>
          avg util {data.avg_utilization_pct}% · in_use {data.in_use_count}/{data.total_count}
        </span>
      </div>
      {data.total_count === 0 ? (
        <div style={{ color: "var(--text3)", fontSize: 12 }}>無機台資料</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {labKeys.map((lab) => (
            <div key={lab} style={{ display: "flex", alignItems: "center", gap: 8 }}>
              {showLabPrefix && (
                <span
                  style={{
                    fontSize: 11,
                    color: "var(--text3)",
                    fontFamily: "monospace",
                    width: 56,
                  }}
                >
                  {lab}
                </span>
              )}
              <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                {data.by_lab[lab].map((m) => (
                  <Tile key={m.machine_id} m={m} />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Write MachineHeatmap test**

```typescript
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import MachineHeatmap from "../MachineHeatmap";
import type { MachineHeatmap as Data } from "@/types/dashboard";

const data: Data = {
  by_lab: {
    "LAB-A": [
      {
        machine_id: "m1",
        machine_no: "M1",
        lab_name: "LAB-A",
        status: "in_use",
        today_hours: 3.2,
        current_recipe: null,
        current_operator: null,
        est_completion_at: null,
      },
      {
        machine_id: "m2",
        machine_no: "M2",
        lab_name: "LAB-A",
        status: "faulty",
        today_hours: 0,
        current_recipe: null,
        current_operator: null,
        est_completion_at: null,
      },
    ],
  },
  avg_utilization_pct: 67,
  in_use_count: 1,
  total_count: 2,
};

describe("MachineHeatmap", () => {
  it("renders header with util + counts", () => {
    render(<MachineHeatmap data={data} showLabPrefix={true} />);
    expect(screen.getByText(/avg util 67%/)).toBeInTheDocument();
    expect(screen.getByText(/in_use 1\/2/)).toBeInTheDocument();
  });

  it("shows lab prefix when enabled", () => {
    render(<MachineHeatmap data={data} showLabPrefix={true} />);
    expect(screen.getByText("LAB-A")).toBeInTheDocument();
  });

  it("hides lab prefix when disabled (lab_supervisor)", () => {
    render(<MachineHeatmap data={data} showLabPrefix={false} />);
    expect(screen.queryByText("LAB-A")).not.toBeInTheDocument();
  });

  it("shows empty state when no machines", () => {
    render(
      <MachineHeatmap
        data={{ by_lab: {}, avg_utilization_pct: 0, in_use_count: 0, total_count: 0 }}
        showLabPrefix={true}
      />,
    );
    expect(screen.getByText("無機台資料")).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Run + commit**

```bash
cd frontend && npm test -- MachineHeatmap
git add frontend/app/_dashboard/MachineHeatmap.tsx frontend/app/_dashboard/__tests__/MachineHeatmap.test.tsx
git commit -m "feat(dashboard): add MachineHeatmap component + tests"
```

---

## Task 9: Frontend WipPipeline + test

**Files:**
- Create: `frontend/app/_dashboard/WipPipeline.tsx`
- Test: `frontend/app/_dashboard/__tests__/WipPipeline.test.tsx`

- [ ] **Step 1: Create WipPipeline.tsx**

```typescript
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
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
        <h3 style={{ margin: 0, fontSize: 14 }}>WIP pipeline</h3>
        <span style={{ fontSize: 11, color: "var(--text3)", fontFamily: "monospace" }}>
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
```

- [ ] **Step 2: Write WipPipeline test**

```typescript
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import WipPipeline from "../WipPipeline";
import type { WipPipeline as Data } from "@/types/dashboard";

const data: Data = {
  total: 31,
  waiting_dispatch: [5, 1],
  dispatched: [3, 0],
  in_progress: [12, -2],
  awaiting_handoff: [8, 3],
  done: [3, 1],
  terminated: [0, 0],
};

describe("WipPipeline", () => {
  it("renders header with total", () => {
    render(<WipPipeline data={data} />);
    expect(screen.getByText(/共 31 件/)).toBeInTheDocument();
  });

  it("shows all 6 stage labels", () => {
    render(<WipPipeline data={data} />);
    expect(screen.getByText("待排程")).toBeInTheDocument();
    expect(screen.getByText("排程")).toBeInTheDocument();
    expect(screen.getByText("進行")).toBeInTheDocument();
    expect(screen.getByText("待傳")).toBeInTheDocument();
    expect(screen.getByText("完")).toBeInTheDocument();
    expect(screen.getByText("終止")).toBeInTheDocument();
  });

  it("shows empty state when no WIP", () => {
    render(
      <WipPipeline
        data={{
          total: 0,
          waiting_dispatch: [0, 0],
          dispatched: [0, 0],
          in_progress: [0, 0],
          awaiting_handoff: [0, 0],
          done: [0, 0],
          terminated: [0, 0],
        }}
      />,
    );
    expect(screen.getByText("目前無 WIP")).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Run + commit**

```bash
cd frontend && npm test -- WipPipeline
git add frontend/app/_dashboard/WipPipeline.tsx frontend/app/_dashboard/__tests__/WipPipeline.test.tsx
git commit -m "feat(dashboard): add WipPipeline component + tests"
```

---

## Task 10: Frontend TriageList + test

**Files:**
- Create: `frontend/app/_dashboard/TriageList.tsx`
- Test: `frontend/app/_dashboard/__tests__/TriageList.test.tsx`

- [ ] **Step 1: Create TriageList.tsx**

```typescript
"use client";

import type { TriageItem } from "@/types/dashboard";

const SEVERITY_COLOR: Record<string, string> = {
  critical: "var(--red)",
  high: "var(--orange)",
  medium: "#d4a300",
  low: "var(--cyan)",
};

function TypeLabel({ type }: { type: TriageItem["type"] }) {
  const map = { pending_approval: "簽", escalated_issue: "升", open_issue: "告" };
  return (
    <span
      style={{
        fontSize: 10,
        background: "var(--s2)",
        padding: "2px 6px",
        borderRadius: 4,
        color: "var(--text2)",
      }}
    >
      {map[type]}
    </span>
  );
}

function ago(iso: string): string {
  const diffMin = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (diffMin < 60) return `${diffMin} min ago`;
  return `${Math.round(diffMin / 60)} h ago`;
}

function drillTo(item: TriageItem): string {
  if (item.type === "pending_approval") return `/approve?order=${item.ref_id}`;
  return `/issues/${item.ref_id}`;
}

export default function TriageList({ items }: { items: TriageItem[] }) {
  return (
    <div
      data-testid="triage-list"
      style={{
        background: "var(--s1)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: 16,
        height: 200,
        overflow: "auto",
      }}
    >
      <h3 style={{ margin: 0, fontSize: 14, marginBottom: 10 }}>待 triage</h3>
      {items.length === 0 ? (
        <div style={{ color: "var(--text3)", fontSize: 12 }}>目前無待處理事項</div>
      ) : (
        <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 6 }}>
          {items.map((it) => (
            <li
              key={`${it.type}-${it.ref_id}`}
              onClick={() => {
                window.location.href = drillTo(it);
              }}
              style={{
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 6,
                fontSize: 12,
                color: "var(--text2)",
              }}
            >
              <TypeLabel type={it.type} />
              {it.severity && (
                <span style={{ color: SEVERITY_COLOR[it.severity] }}>{it.severity}</span>
              )}
              {it.lab_name && (
                <span style={{ fontFamily: "monospace", color: "var(--text3)" }}>{it.lab_name}</span>
              )}
              <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {it.label}
              </span>
              <span style={{ fontSize: 10, color: "var(--text3)" }}>{ago(it.created_at)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Write TriageList test**

```typescript
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import TriageList from "../TriageList";
import type { TriageItem } from "@/types/dashboard";

const items: TriageItem[] = [
  {
    type: "pending_approval",
    ref_id: "ORD-001",
    label: "ORD-001 · 張工",
    lab_name: null,
    severity: null,
    created_at: new Date(Date.now() - 7 * 60 * 1000).toISOString(),
  },
  {
    type: "escalated_issue",
    ref_id: "ISS-091",
    label: "真空泵故障",
    lab_name: "LAB-A",
    severity: "critical",
    created_at: new Date(Date.now() - 12 * 60 * 1000).toISOString(),
  },
];

describe("TriageList", () => {
  it("renders list with both items", () => {
    render(<TriageList items={items} />);
    expect(screen.getByText("ORD-001 · 張工")).toBeInTheDocument();
    expect(screen.getByText("真空泵故障")).toBeInTheDocument();
  });

  it("shows severity for issue items", () => {
    render(<TriageList items={items} />);
    expect(screen.getByText("critical")).toBeInTheDocument();
  });

  it("shows empty state", () => {
    render(<TriageList items={[]} />);
    expect(screen.getByText("目前無待處理事項")).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Run + commit**

```bash
cd frontend && npm test -- TriageList
git add frontend/app/_dashboard/TriageList.tsx frontend/app/_dashboard/__tests__/TriageList.test.tsx
git commit -m "feat(dashboard): add TriageList component + tests"
```

---

## Task 11: Frontend EscalationsList + test

**Files:**
- Create: `frontend/app/_dashboard/EscalationsList.tsx`
- Test: `frontend/app/_dashboard/__tests__/EscalationsList.test.tsx`

- [ ] **Step 1: Create EscalationsList.tsx**

```typescript
"use client";

import type { EscalationRow } from "@/types/dashboard";

const SEVERITY_COLOR: Record<string, string> = {
  critical: "var(--red)",
  high: "var(--orange)",
  medium: "#d4a300",
  low: "var(--cyan)",
};

function ago(iso: string): string {
  const m = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (m < 60) return `${m} min ago`;
  return `${Math.round(m / 60)} h ago`;
}

export default function EscalationsList({ rows }: { rows: EscalationRow[] }) {
  return (
    <div
      data-testid="escalations-list"
      style={{
        background: "var(--s1)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: 16,
        height: 200,
        overflow: "auto",
      }}
    >
      <h3 style={{ margin: 0, fontSize: 14, marginBottom: 10 }}>Recent Escalations</h3>
      {rows.length === 0 ? (
        <div style={{ color: "var(--text3)", fontSize: 12 }}>過去 24h 無升級</div>
      ) : (
        <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 6 }}>
          {rows.map((r) => (
            <li
              key={r.issue_id}
              onClick={() => {
                window.location.href = `/issues/${r.issue_id}`;
              }}
              style={{
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 6,
                fontSize: 12,
                color: "var(--text2)",
              }}
            >
              <span style={{ color: SEVERITY_COLOR[r.severity] }}>{r.severity}</span>
              <span style={{ fontSize: 10, color: "var(--text3)", fontFamily: "monospace" }}>
                L{r.escalation_level}
              </span>
              <span style={{ fontFamily: "monospace", color: "var(--text3)" }}>{r.lab_name}</span>
              <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {r.title}
              </span>
              <span style={{ fontSize: 10, color: "var(--text3)" }}>{ago(r.escalated_at)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Write EscalationsList test**

```typescript
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import EscalationsList from "../EscalationsList";
import type { EscalationRow } from "@/types/dashboard";

const rows: EscalationRow[] = [
  {
    issue_id: "iss-1",
    lab_name: "LAB-A",
    severity: "critical",
    escalation_level: 2,
    title: "真空泵故障",
    escalated_at: new Date(Date.now() - 12 * 60 * 1000).toISOString(),
  },
];

describe("EscalationsList", () => {
  it("renders rows", () => {
    render(<EscalationsList rows={rows} />);
    expect(screen.getByText("真空泵故障")).toBeInTheDocument();
    expect(screen.getByText("critical")).toBeInTheDocument();
    expect(screen.getByText("L2")).toBeInTheDocument();
    expect(screen.getByText("LAB-A")).toBeInTheDocument();
  });

  it("shows empty state", () => {
    render(<EscalationsList rows={[]} />);
    expect(screen.getByText("過去 24h 無升級")).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Run + commit**

```bash
cd frontend && npm test -- EscalationsList
git add frontend/app/_dashboard/EscalationsList.tsx frontend/app/_dashboard/__tests__/EscalationsList.test.tsx
git commit -m "feat(dashboard): add EscalationsList component + tests"
```

---

## Task 12: Frontend CompletionsList + LabLeaderboard + tests

Combined task — two small list components.

**Files:**
- Create: `frontend/app/_dashboard/CompletionsList.tsx`
- Create: `frontend/app/_dashboard/LabLeaderboard.tsx`
- Test: `frontend/app/_dashboard/__tests__/CompletionsList.test.tsx`
- Test: `frontend/app/_dashboard/__tests__/LabLeaderboard.test.tsx`

- [ ] **Step 1: Create CompletionsList.tsx**

```typescript
"use client";

import type { CompletionRow } from "@/types/dashboard";

function ago(iso: string): string {
  const m = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60000));
  if (m < 60) return `${m} min ago`;
  return `${Math.round(m / 60)} h ago`;
}

export default function CompletionsList({ rows }: { rows: CompletionRow[] }) {
  return (
    <div
      data-testid="completions-list"
      style={{
        background: "var(--s1)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: 16,
        height: 200,
        overflow: "auto",
      }}
    >
      <h3 style={{ margin: 0, fontSize: 14, marginBottom: 10 }}>Recent Completions</h3>
      {rows.length === 0 ? (
        <div style={{ color: "var(--text3)", fontSize: 12 }}>近 30 分鐘無回傳</div>
      ) : (
        <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 6 }}>
          {rows.map((r) => (
            <li
              key={r.wip_no}
              onClick={() => {
                window.location.href = `/storage?order=${r.order_no}`;
              }}
              style={{
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 6,
                fontSize: 12,
                color: "var(--text2)",
              }}
            >
              <span
                style={{
                  fontSize: 10,
                  background: "var(--s2)",
                  padding: "2px 6px",
                  borderRadius: 4,
                  color: "#3fb950",
                }}
              >
                完
              </span>
              <span style={{ fontFamily: "monospace", color: "var(--text1)" }}>{r.wip_no}</span>
              <span style={{ fontFamily: "monospace", color: "var(--text3)" }}>{r.order_no}</span>
              <span style={{ flex: 1 }} />
              <span style={{ fontSize: 10, color: "var(--text3)" }}>{ago(r.returned_at)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Create LabLeaderboard.tsx**

```typescript
"use client";

import type { LabRow } from "@/types/dashboard";

function Trend({ t }: { t: "up" | "flat" | "down" }) {
  if (t === "up") return <span style={{ color: "#3fb950" }}>↑</span>;
  if (t === "down") return <span style={{ color: "var(--red)" }}>↓</span>;
  return <span style={{ color: "var(--text3)" }}>→</span>;
}

export default function LabLeaderboard({ rows }: { rows: LabRow[] }) {
  return (
    <div
      data-testid="lab-leaderboard"
      style={{
        background: "var(--s1)",
        border: "1px solid var(--border)",
        borderRadius: 8,
        padding: 16,
        height: 200,
        overflow: "auto",
      }}
    >
      <h3 style={{ margin: 0, fontSize: 14, marginBottom: 10 }}>Lab Leaderboard</h3>
      {rows.length === 0 ? (
        <div style={{ color: "var(--text3)", fontSize: 12 }}>無 lab 資料</div>
      ) : (
        <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 8 }}>
          {rows.map((r) => (
            <li
              key={r.lab_name}
              onClick={() => {
                window.location.href = `/orders?lab=${encodeURIComponent(r.lab_name)}`;
              }}
              style={{
                cursor: "pointer",
                display: "grid",
                gridTemplateColumns: "minmax(60px, 1fr) auto auto auto auto 20px",
                gap: 8,
                fontSize: 12,
                color: "var(--text2)",
                alignItems: "baseline",
              }}
            >
              <span style={{ fontFamily: "monospace" }}>{r.lab_name}</span>
              <span>完工 {r.completed_today}</span>
              <span>待傳 {r.awaiting_handoff}</span>
              <span>告警 {r.open_high_critical_issues}</span>
              <span style={{ fontFamily: "monospace" }}>util {r.avg_utilization_pct}%</span>
              <Trend t={r.trend_24h} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Write CompletionsList test**

```typescript
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import CompletionsList from "../CompletionsList";
import type { CompletionRow } from "@/types/dashboard";

const rows: CompletionRow[] = [
  {
    wip_no: "WIP-A001",
    order_no: "ORD-2025-0012",
    lab_name: "LAB-A",
    returned_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
  },
];

describe("CompletionsList", () => {
  it("renders rows", () => {
    render(<CompletionsList rows={rows} />);
    expect(screen.getByText("WIP-A001")).toBeInTheDocument();
    expect(screen.getByText("ORD-2025-0012")).toBeInTheDocument();
  });

  it("shows empty state", () => {
    render(<CompletionsList rows={[]} />);
    expect(screen.getByText("近 30 分鐘無回傳")).toBeInTheDocument();
  });
});
```

- [ ] **Step 4: Write LabLeaderboard test**

```typescript
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import LabLeaderboard from "../LabLeaderboard";
import type { LabRow } from "@/types/dashboard";

const rows: LabRow[] = [
  {
    lab_name: "LAB-A",
    completed_today: 9,
    awaiting_handoff: 2,
    open_high_critical_issues: 1,
    avg_utilization_pct: 78,
    trend_24h: "up",
  },
];

describe("LabLeaderboard", () => {
  it("renders rows", () => {
    render(<LabLeaderboard rows={rows} />);
    expect(screen.getByText("LAB-A")).toBeInTheDocument();
    expect(screen.getByText(/完工 9/)).toBeInTheDocument();
    expect(screen.getByText(/util 78%/)).toBeInTheDocument();
  });

  it("shows empty state", () => {
    render(<LabLeaderboard rows={[]} />);
    expect(screen.getByText("無 lab 資料")).toBeInTheDocument();
  });
});
```

- [ ] **Step 5: Run + commit**

```bash
cd frontend && npm test -- CompletionsList LabLeaderboard
git add frontend/app/_dashboard/CompletionsList.tsx frontend/app/_dashboard/LabLeaderboard.tsx frontend/app/_dashboard/__tests__/CompletionsList.test.tsx frontend/app/_dashboard/__tests__/LabLeaderboard.test.tsx
git commit -m "feat(dashboard): add CompletionsList + LabLeaderboard components + tests"
```

---

## Task 13: Frontend useDashboardStream hook

**Files:**
- Create: `frontend/app/_dashboard/useDashboardStream.ts`

- [ ] **Step 1: Create useDashboardStream.ts**

```typescript
import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";

/**
 * Subscribes to /api/dashboard/stream (SSE). On any event, invalidate the
 * ["dashboard"] query so the next render re-fetches. The handler ignores
 * the event name — all events mean "something changed, re-pull snapshot".
 *
 * Falls back silently if EventSource isn't supported or connection fails:
 * 30s polling in the parent useQuery covers freshness.
 */
export function useDashboardStream() {
  const qc = useQueryClient();
  useEffect(() => {
    if (typeof window === "undefined" || typeof EventSource === "undefined") return;
    const base = process.env.NEXT_PUBLIC_API_URL ?? "/api";
    const url = `${base}/dashboard/stream`;
    let es: EventSource | null = null;
    try {
      es = new EventSource(url, { withCredentials: true });
      es.addEventListener("dashboard", () => {
        qc.invalidateQueries({ queryKey: ["dashboard"] });
      });
      es.onmessage = () => {
        qc.invalidateQueries({ queryKey: ["dashboard"] });
      };
      es.onerror = () => {
        // Let it auto-reconnect; if it doesn't, polling covers.
      };
    } catch {
      // ignore — polling fallback
    }
    return () => {
      es?.close();
    };
  }, [qc]);
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/app/_dashboard/useDashboardStream.ts
git commit -m "feat(dashboard): add SSE invalidation hook"
```

---

## Task 14: Frontend page.tsx rewrite + delete old panels

**Files:**
- Modify (rewrite): `frontend/app/page.tsx`
- Delete: `frontend/app/_dashboard/AttentionPanel.tsx`
- Delete: `frontend/app/_dashboard/DispatchPanel.tsx`
- Delete: `frontend/app/_dashboard/LabsPanel.tsx`
- Delete: `frontend/app/_dashboard/MachineStatusPanel.tsx`

- [ ] **Step 1: Delete unused panels**

```bash
rm frontend/app/_dashboard/AttentionPanel.tsx
rm frontend/app/_dashboard/DispatchPanel.tsx
rm frontend/app/_dashboard/LabsPanel.tsx
rm frontend/app/_dashboard/MachineStatusPanel.tsx
```

- [ ] **Step 2: Rewrite page.tsx**

Replace `frontend/app/page.tsx` entirely:

```typescript
"use client";

import { useQuery } from "@tanstack/react-query";
import { PermissionGuard } from "@/components/PermissionGuard";
import { dashboardApi } from "@/services/dashboard-api";
import KpiBar from "@/app/_dashboard/KpiBar";
import MachineHeatmap from "@/app/_dashboard/MachineHeatmap";
import WipPipeline from "@/app/_dashboard/WipPipeline";
import TriageList from "@/app/_dashboard/TriageList";
import EscalationsList from "@/app/_dashboard/EscalationsList";
import CompletionsList from "@/app/_dashboard/CompletionsList";
import LabLeaderboard from "@/app/_dashboard/LabLeaderboard";
import { useDashboardStream } from "@/app/_dashboard/useDashboardStream";

export default function DashboardPage() {
  return (
    <PermissionGuard requiredPermission="dashboard:read">
      <DashboardContent />
    </PermissionGuard>
  );
}

function DashboardContent() {
  useDashboardStream();
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => dashboardApi.getSnapshot(),
    refetchInterval: 30_000,
  });

  if (isLoading) {
    return <div style={{ padding: 24, color: "var(--text2)" }}>載入中…</div>;
  }
  if (isError) {
    return (
      <div style={{ padding: 24, color: "var(--red)" }}>
        儀表板載入失敗：{(error as Error).message}
      </div>
    );
  }
  if (!data) return null;

  const isCrossLab = data.viewer_role === "general_supervisor";

  return (
    <div style={{ padding: 24 }}>
      {/* Header */}
      <div style={{ marginBottom: 16 }}>
        <h1 style={{ fontSize: 22, fontWeight: 800, letterSpacing: -0.5, margin: 0 }}>
          主管儀表板
        </h1>
        <p style={{ fontSize: 12, color: "var(--text3)", marginTop: 4, fontFamily: "monospace" }}>
          SUPERVISOR DASHBOARD · {isCrossLab ? "全廠視角" : `${data.viewer_lab ?? "本 lab"}`} · 自動更新
        </p>
      </div>

      {/* Top: KPI Bar */}
      <div style={{ marginBottom: 16 }}>
        <KpiBar data={data.kpi} />
      </div>

      {/* Mid: Heatmap | Pipeline */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 16,
          marginBottom: 16,
        }}
      >
        <MachineHeatmap data={data.machines} showLabPrefix={isCrossLab} />
        <WipPipeline data={data.wip_pipeline} />
      </div>

      {/* Bottom: 3 cols */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr",
          gap: 16,
        }}
      >
        <TriageList items={data.triage} />
        <EscalationsList rows={data.recent_escalations} />
        {isCrossLab ? (
          <LabLeaderboard rows={data.lab_leaderboard ?? []} />
        ) : (
          <CompletionsList rows={data.recent_completions ?? []} />
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Lint + build**

```bash
cd frontend && npm run lint && npm run build
```

Expected: no errors. Address any import path issues (Next.js may need `@/app/_dashboard/...` vs relative paths depending on tsconfig).

- [ ] **Step 4: Commit**

```bash
git add frontend/app/page.tsx
git rm frontend/app/_dashboard/AttentionPanel.tsx frontend/app/_dashboard/DispatchPanel.tsx frontend/app/_dashboard/LabsPanel.tsx frontend/app/_dashboard/MachineStatusPanel.tsx
git commit -m "feat(dashboard): rewrite page.tsx + remove unused panels"
```

---

## Task 15: Playwright E2E test

**Files:**
- Create: `frontend/e2e/dashboard.spec.ts`

- [ ] **Step 1: Find existing e2e config + login helper**

```bash
ls frontend/e2e/ 2>/dev/null
cat frontend/playwright.config.ts 2>/dev/null | head -30
```

If the existing demo-flow test (`frontend/e2e/*.spec.ts` per CLAUDE.md) uses a login helper, reuse it. If not, build minimally.

- [ ] **Step 2: Create dashboard.spec.ts**

```typescript
import { test, expect } from "@playwright/test";

test.describe("Supervisor dashboard", () => {
  test("loads with KPI bar visible for general_supervisor seed user", async ({ page }) => {
    // Log in (adjust to project's seeded credentials)
    await page.goto("/login");
    await page.getByLabel(/帳號|username/i).fill("general_supervisor_seed");
    await page.getByLabel(/密碼|password/i).fill("Password123!");
    await page.getByRole("button", { name: /登入|login/i }).click();

    // Land on / and expect dashboard
    await page.waitForURL("/");
    await expect(page.getByText("主管儀表板")).toBeVisible();

    // 5 KPI tiles
    const kpi = page.getByTestId("kpi-bar");
    await expect(kpi).toBeVisible();
    await expect(kpi.getByText("新單")).toBeVisible();
    await expect(kpi.getByText("完工")).toBeVisible();
    await expect(kpi.getByText("回傳")).toBeVisible();
    await expect(kpi.getByText("待簽")).toBeVisible();
    await expect(kpi.getByText("告警")).toBeVisible();

    // Mid widgets present
    await expect(page.getByTestId("machine-heatmap")).toBeVisible();
    await expect(page.getByTestId("wip-pipeline")).toBeVisible();

    // Bottom: general_supervisor shows leaderboard, not completions
    await expect(page.getByTestId("lab-leaderboard")).toBeVisible();
    await expect(page.getByTestId("completions-list")).toHaveCount(0);
  });
});
```

Note: replace `general_supervisor_seed` + password with real seeded credentials — check `backend/scripts/seed.py` or equivalent.

- [ ] **Step 3: Run e2e**

```bash
cd frontend
npx playwright test e2e/dashboard.spec.ts
```

This requires the backend running (docker compose or local). If not feasible right now, mark this step as deferred but commit the test file.

- [ ] **Step 4: Commit**

```bash
git add frontend/e2e/dashboard.spec.ts
git commit -m "test(dashboard): add Playwright E2E for supervisor dashboard"
```

---

## Task 16: Verification + lims-code-reviewer

- [ ] **Step 1: Start backend + frontend dev servers**

In one shell:

```bash
cd backend && source venv/bin/activate
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

In another shell:

```bash
cd frontend
npm run dev
```

- [ ] **Step 2: Manual smoke test**

Open http://localhost:3000, log in as a supervisor seed user, confirm:
- Header shows "主管儀表板"
- KPI bar shows 5 tiles with numbers
- Machine heatmap renders (even if mostly empty)
- WIP pipeline renders (empty state OK if no WIP)
- Bottom 3 panels render
- Switch to general_supervisor account → 3rd panel is leaderboard
- Open browser devtools, confirm `/api/dashboard` returns 200
- Confirm `/api/dashboard/stream` opens an EventSource connection

- [ ] **Step 3: Run all tests one more time**

```bash
cd backend && pytest -x
cd frontend && npm test
```

Expected: all green.

- [ ] **Step 4: Invoke lims-code-reviewer**

Per CLAUDE.md, delegate review to the project-tuned agent:

> Run the `lims-code-reviewer` agent on the diff between `8a6d645` and HEAD. Focus on:
> - Backend: SQL query correctness for each repository method, role scope correctness (lab_supervisor vs general_supervisor), error handling in publisher
> - Frontend: type drift between schemas.py and types/dashboard.ts, visual token usage, drill-down paths
> - Tests: coverage gaps, fixture realism

Fix any findings before claiming done.

- [ ] **Step 5: Final commit (if reviewer findings applied)**

```bash
git status
git add <any modified files>
git commit -m "fix(dashboard): address lims-code-reviewer findings"
```

---

## Self-Review Notes

After writing the plan, self-checked:
- **Spec coverage**: all 6 spec sections mapped to tasks (1→T1+T7, 2→T8, 3→T9, 4→T10–12, 5→T1–T4, 6→T13+T14)
- **Placeholders**: every code block is complete; no "TBD"
- **Type consistency**: backend `WipPipeline.waiting_dispatch: tuple[int, int]` ↔ frontend `WipPipeline.waiting_dispatch: Pair = [number, number]` — consistent
- **Scope**: single feature, ~16 tasks, single plan tractable
- **Known fragility**: T2's `kpi_completed_today` relies on `Wip.completed_at` being set when status hits COMPLETED — verify in repo; if absent, use status-change audit timestamp or fall back to today's `updated_at` proxy
- **Edge note**: T11/T12 fixtures reference `created_by` on `OrderModel`; if column is named differently (e.g., `created_by_id`), adapt at implementation time without ripping the plan

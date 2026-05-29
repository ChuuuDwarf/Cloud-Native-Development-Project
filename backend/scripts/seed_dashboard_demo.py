"""Idempotent dashboard-demo seed: lights up every dashboard widget for "today".

Runs AFTER ``seed_dev`` / ``seed_machines`` / ``seed_experiments``. Doesn't
modify the existing 2024-dated seed corpus; only adds new natural-key rows
prefixed ``DEMO-*`` (machines / recipes use shorter ``D-`` prefixes to fit
their 32-char natural-key columns).

Why this exists
---------------
The original three seed scripts put every Order / Wip / Report timestamp in
mid-2024 and most rows in LAB-A only, so every dashboard widget renders mostly
empty for "today":

* KPI tiles read zero across the board (no rolling-24h activity).
* Hourly sparklines / throughput chart are all-zero.
* Machine heatmap only shows LAB-A.
* WIP pipeline shows one bucket.
* Triage / Recent Escalations are empty.
* Leaderboard / per_lab_util is single-row.

This script complements the existing corpus with new rows whose timestamps
sit in the **rolling trailing 24h** window the dashboard queries against
(``[now-24h, now)``), spread across **all five labs**, in every WIP /
issue / machine status bucket the dashboard cares about.

Status-string conventions (carry forward from review)
-----------------------------------------------------
* ``Wip.status`` writes the literal DB CHECK vocab (``waiting_schedule /
  scheduled / dispatched / running / paused / completed / terminated /
  cancelled``). The ``WipStatus`` enum's ``WAITING_DISPATCH`` /
  ``UNLOADED`` / ``WAITING_CONFIRM`` values never make it into the DB.
* ``Wip.lab_name`` is the **display name** (e.g. ``電性測試實驗室``), NOT the
  lab code. ``Machine.lab`` is the lab **code** (e.g. ``LAB-A``).
* ``Wip.completed_at`` / ``Report.created_at`` are tz-naive TIMESTAMP.
  ``OrderModel.created_at`` / ``Issue.updated_at`` are TIMESTAMPTZ. Use
  ``_naive_now()`` vs ``_aware_now()`` correctly.
* ``OrderItemModel.lab_id`` stores the lab **code**.
* ``Issue.lab_id`` is the lab UUID.
* ``Notification.source_id`` stores ``str(issue.id)`` for issue notifications.
* ``Report.wip_id`` holds the business ``wip_no`` (string, not UUID).
* ``wips.lab_closed`` column exists at DB-level (migration
  ``35aeb03a89e9``) but is NOT on the ORM model. Don't touch it.
"""

from __future__ import annotations

import asyncio
import random
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.common.enums import (  # noqa: E402
    IssueStatus,
    IssueType,
    NotificationChannel,
    NotificationStatus,
    ReportStatus,
    Severity,
)
from app.common.enums.order_status import OrderStatus  # noqa: E402
from app.common.enums.role_d_zh import REPORT_ZH  # noqa: E402
from app.core.database import AsyncSessionLocal  # noqa: E402
from app.db.models import (  # noqa: E402
    Issue,
    Lab,
    LabCapability,
    Machine,
    Notification,
    OrderItemModel,
    OrderModel,
    Recipe,
    Report,
    ReportVersion,
    User,
    Wip,
    WipExecution,
)

# Deterministic randomness so re-runs land identical jitter values inside the
# rolling 24h window (only the wall clock moves).
RNG = random.Random(42)

# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------


def _aware_now() -> datetime:
    """tz-aware now for TIMESTAMPTZ columns (Order.created_at, Issue.updated_at)."""
    return datetime.now(UTC)


def _naive_now() -> datetime:
    """tz-naive now for plain TIMESTAMP columns (Wip.completed_at, Report.created_at)."""
    return datetime.now(UTC).replace(tzinfo=None)


def _jitter_hours_ago(hours_back: float, *, naive: bool) -> datetime:
    """Return ``now - hours_back`` plus +/- 15min jitter for visual variety."""
    base = _naive_now() if naive else _aware_now()
    jitter_minutes = RNG.randint(-15, 15)
    return base - timedelta(hours=hours_back, minutes=-jitter_minutes)


def _spread_24h(n: int, *, naive: bool, max_hours_back: float = 23.5) -> list[datetime]:
    """Return ``n`` timestamps spread across the rolling 24h window.

    Each timestamp lands at a different hour offset so the hourly-bucket
    series (new_orders / completed / returned) has ``n`` filled buckets
    out of 24. If ``n > 24`` we wrap around with finer offsets.
    """
    # Cap at 23.5h-back so the first bucket isn't exactly on the lower
    # bound (which sometimes gets dropped by date_trunc rounding).
    step = max_hours_back / max(n, 1)
    return [
        _jitter_hours_ago(max_hours_back - step * i, naive=naive)
        # spread evenly with the *latest* one (smallest hours_back) at
        # index 0 — keeps "most recent" rows readable in human terms.
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Lab definitions — add LAB-D / LAB-E so all 5 labs exist for cross-lab demos.
# ---------------------------------------------------------------------------

# code, display_name, capacity, capabilities — capabilities feed the lab
# leaderboard / machine heatmap label resolution.
DEMO_LABS: list[tuple[str, str, int, list[str]]] = [
    ("LAB-D", "封裝測試實驗室", 8, ["WB", "DA", "WLBI"]),
    ("LAB-E", "製程實驗室", 10, ["Litho", "Etch", "Depo"]),
]


# ---------------------------------------------------------------------------
# Machines — 16 new, distributed so every lab has 5 total and every status
# is represented at least twice. Natural key prefix: D-<LAB>-<NN>.
# Each tuple = (machine_id, name, lab_code, status, utilization, supported_items, owner)
# ---------------------------------------------------------------------------

DEMO_MACHINES: list[dict] = [
    # LAB-A — top up to 5 total. seed_machines already added: TEM-001, XRD-002,
    # SEM-001, THR-001, OPT-001, CHM-001, EDX-001, IV-001, TC-001 (all LAB-A).
    # We won't add more LAB-A machines (it already has 9); we use those + add
    # for the other labs. To get "5/lab" we just add 4 per non-LAB-A lab.
    # LAB-B (電性測試)
    {
        "machine_id": "D-B-01",
        "name": "B 區探針台",
        "lab": "LAB-B",
        "status": "使用中",
        "utilization": 78,
        "supported_items": ["IV"],
        "owner": "王小明",
    },
    {
        "machine_id": "D-B-02",
        "name": "B 區半導體參數量測 #2",
        "lab": "LAB-B",
        "status": "使用中",
        "utilization": 63,
        "supported_items": ["IV"],
        "owner": "王小明",
    },
    {
        "machine_id": "D-B-03",
        "name": "B 區 ESD 模擬器",
        "lab": "LAB-B",
        "status": "閒置",
        "utilization": 22,
        "supported_items": ["ESD"],
        "owner": "林妏媞",
    },
    {
        "machine_id": "D-B-04",
        "name": "B 區 CV 量測儀",
        "lab": "LAB-B",
        "status": "保養中",
        "utilization": 0,
        "supported_items": ["CV"],
        "owner": "林妏媞",
    },
    # LAB-C (可靠度)
    {
        "machine_id": "D-C-01",
        "name": "C 區高溫老化爐",
        "lab": "LAB-C",
        "status": "使用中",
        "utilization": 88,
        "supported_items": ["HTOL"],
        "owner": "陳美秀",
    },
    {
        "machine_id": "D-C-02",
        "name": "C 區溫度循環試驗機 #2",
        "lab": "LAB-C",
        "status": "閒置",
        "utilization": 34,
        "supported_items": ["TC"],
        "owner": "陳美秀",
    },
    {
        "machine_id": "D-C-03",
        "name": "C 區 ESD 模擬器",
        "lab": "LAB-C",
        "status": "故障中",
        "utilization": 0,
        "supported_items": ["ESD"],
        "owner": "周秉倫",
    },
    {
        "machine_id": "D-C-04",
        "name": "C 區壽命試驗機",
        "lab": "LAB-C",
        "status": "停用",
        "utilization": 0,
        "supported_items": ["HTOL"],
        "owner": "周秉倫",
    },
    # LAB-D (封裝測試)
    {
        "machine_id": "D-D-01",
        "name": "D 區打線機",
        "lab": "LAB-D",
        "status": "使用中",
        "utilization": 70,
        "supported_items": ["WB"],
        "owner": "黃工",
    },
    {
        "machine_id": "D-D-02",
        "name": "D 區黏晶機",
        "lab": "LAB-D",
        "status": "使用中",
        "utilization": 58,
        "supported_items": ["DA"],
        "owner": "黃工",
    },
    {
        "machine_id": "D-D-03",
        "name": "D 區晶圓燒機系統",
        "lab": "LAB-D",
        "status": "閒置",
        "utilization": 25,
        "supported_items": ["WLBI"],
        "owner": "蔡工",
    },
    {
        "machine_id": "D-D-04",
        "name": "D 區保養中老化爐",
        "lab": "LAB-D",
        "status": "保養中",
        "utilization": 0,
        "supported_items": ["HTOL"],
        "owner": "蔡工",
    },
    # LAB-E (製程)
    {
        "machine_id": "D-E-01",
        "name": "E 區黃光機",
        "lab": "LAB-E",
        "status": "使用中",
        "utilization": 81,
        "supported_items": ["Litho"],
        "owner": "趙工",
    },
    {
        "machine_id": "D-E-02",
        "name": "E 區乾蝕刻機",
        "lab": "LAB-E",
        "status": "閒置",
        "utilization": 30,
        "supported_items": ["Etch"],
        "owner": "趙工",
    },
    {
        "machine_id": "D-E-03",
        "name": "E 區金屬沉積機",
        "lab": "LAB-E",
        "status": "閒置",
        "utilization": 28,
        "supported_items": ["Depo"],
        "owner": "鄭工",
    },
    {
        "machine_id": "D-E-04",
        "name": "E 區故障蝕刻機",
        "lab": "LAB-E",
        "status": "故障中",
        "utilization": 0,
        "supported_items": ["Etch"],
        "owner": "鄭工",
    },
]


# ---------------------------------------------------------------------------
# Recipes — one per supported_item per non-LAB-A lab so the dispatches /
# experiment-runs pages have something to render too.
# ---------------------------------------------------------------------------

DEMO_RECIPES: list[dict] = [
    {
        "recipe_id": "D-RCP-IV-B",
        "name": "B 區 IV 量測 Recipe",
        "version": "v1.0",
        "experiment_item": "IV",
        "machine_ids": ["D-B-01", "D-B-02"],
        "method": "B 區探針 IV 掃描",
        "parameters": {"電壓範圍": "-3V~3V", "步進": "0.05V"},
        "updated_by": "王小明",
    },
    {
        "recipe_id": "D-RCP-CV-B",
        "name": "B 區 CV 量測 Recipe",
        "version": "v1.0",
        "experiment_item": "CV",
        "machine_ids": ["D-B-04"],
        "method": "CV 量測",
        "parameters": {"頻率": "1MHz", "DC 偏壓": "-2V~2V"},
        "updated_by": "林妏媞",
    },
    {
        "recipe_id": "D-RCP-HTOL-C",
        "name": "C 區 HTOL 應力試驗 Recipe",
        "version": "v1.0",
        "experiment_item": "HTOL",
        "machine_ids": ["D-C-01"],
        "method": "高溫加壓壽命試驗",
        "parameters": {"溫度": "125度", "時間": "1000hr"},
        "updated_by": "陳美秀",
    },
    {
        "recipe_id": "D-RCP-ESD-C",
        "name": "C 區 ESD 試驗 Recipe",
        "version": "v1.0",
        "experiment_item": "ESD",
        "machine_ids": ["D-C-03"],
        "method": "HBM / MM ESD 放電",
        "parameters": {"電壓": "2kV", "次數": "3"},
        "updated_by": "周秉倫",
    },
    {
        "recipe_id": "D-RCP-WB-D",
        "name": "D 區打線 Recipe",
        "version": "v1.0",
        "experiment_item": "WB",
        "machine_ids": ["D-D-01"],
        "method": "金線打線",
        "parameters": {"線徑": "25um", "功率": "180mW"},
        "updated_by": "黃工",
    },
    {
        "recipe_id": "D-RCP-DA-D",
        "name": "D 區黏晶 Recipe",
        "version": "v1.0",
        "experiment_item": "DA",
        "machine_ids": ["D-D-02"],
        "method": "銀膠黏晶",
        "parameters": {"溫度": "180度", "壓力": "5N"},
        "updated_by": "黃工",
    },
    {
        "recipe_id": "D-RCP-Litho-E",
        "name": "E 區黃光 Recipe",
        "version": "v1.0",
        "experiment_item": "Litho",
        "machine_ids": ["D-E-01"],
        "method": "曝光 + 顯影",
        "parameters": {"曝光時間": "5s", "光阻": "PR-A"},
        "updated_by": "趙工",
    },
    {
        "recipe_id": "D-RCP-Etch-E",
        "name": "E 區乾蝕刻 Recipe",
        "version": "v1.0",
        "experiment_item": "Etch",
        "machine_ids": ["D-E-02"],
        "method": "電漿蝕刻",
        "parameters": {"氣體": "CF4", "功率": "500W"},
        "updated_by": "趙工",
    },
]


# ---------------------------------------------------------------------------
# Dashboard "shape" plan
# ---------------------------------------------------------------------------
#
# 30 WIPs broken into buckets (matches the brief and the dashboard's
# _WIP_* constants):
#
#   bucket            | count | wips.status      | extras
#   ------------------+-------+------------------+----------------------------
#   waiting_dispatch  |   6   | waiting_schedule | NO Dispatch row
#   dispatched        |   4   | scheduled        | -
#   in_progress       |   8   | running x7, paused x1
#   awaiting_handoff  |   5   | completed        | Report RETURNED, Order IN_PROGRESS
#   done              |   4   | completed        | Report RETURNED, Order WAITING_PICKUP
#   terminated        |   2   | terminated       | abort_requested_at set, has Report
#                                                  RETURNED so it doesn't fall in
#                                                  "completed" bucket but still
#                                                  contributes to "returned" KPI.
#                                                  (We skip Report on terminated to
#                                                  keep semantics tidy.)
#
# Across labs: distribute roughly evenly so per_lab_util / leaderboard / heatmap
# light up everywhere.

LAB_CODES_FOR_WIPS = ["LAB-A", "LAB-B", "LAB-C", "LAB-D", "LAB-E"]

# experiment_item per lab for plausible labels (doesn't need to be perfect).
LAB_EXPERIMENT_ITEMS: dict[str, list[str]] = {
    "LAB-A": ["SEM分析", "EDX", "化學分析"],
    "LAB-B": ["IV", "CV", "ESD"],
    "LAB-C": ["TC", "HTOL", "ESD"],
    "LAB-D": ["WB", "DA", "WLBI"],
    "LAB-E": ["Litho", "Etch", "Depo"],
}


# Order shape:
#   5 PENDING_APPROVAL (created in last 24h)
#   8 IN_PROGRESS — these are the orders WIPs in awaiting_handoff/in_progress
#                   point at (so the dashboard sees in-flight work)
#   4 COMPLETED  — newly created in last 24h (KPI bump)
#   3 WAITING_PICKUP/CLOSED — point of "done" bucket

ORDER_COUNTS = {
    OrderStatus.PENDING_APPROVAL.value: 5,
    OrderStatus.IN_PROGRESS.value: 8,
    OrderStatus.COMPLETED.value: 4,
    OrderStatus.WAITING_PICKUP.value: 3,
}


# ---------------------------------------------------------------------------
# Issues + Notifications
# ---------------------------------------------------------------------------

# (severity, status, escalation_level, hours_ago_for_updated_at)
ISSUE_SPECS: list[tuple[Severity, IssueStatus, int, float]] = [
    # 3 critical
    (Severity.CRITICAL, IssueStatus.ESCALATED, 1, 0.5),
    (Severity.CRITICAL, IssueStatus.ESCALATED, 2, 1.5),
    (Severity.CRITICAL, IssueStatus.OPEN, 0, 6.0),
    # 4 high
    (Severity.HIGH, IssueStatus.ESCALATED, 1, 2.0),
    (Severity.HIGH, IssueStatus.ESCALATED, 2, 3.5),
    (Severity.HIGH, IssueStatus.ASSIGNED, 0, 8.0),
    (Severity.HIGH, IssueStatus.OPEN, 0, 12.0),
    # 2 medium
    (Severity.MEDIUM, IssueStatus.ESCALATED, 1, 3.0),
    (Severity.MEDIUM, IssueStatus.ASSIGNED, 0, 5.0),
    # 1 low
    (Severity.LOW, IssueStatus.OPEN, 0, 18.0),
]


# ---------------------------------------------------------------------------
# Upsert helpers
# ---------------------------------------------------------------------------


async def _upsert_lab(
    session: AsyncSession, code: str, name: str, capacity: int, caps: list[str]
) -> Lab:
    lab = (await session.execute(select(Lab).where(Lab.code == code))).scalar_one_or_none()
    if lab is None:
        lab = Lab(code=code, name=name, capacity=capacity, is_active=True)
        session.add(lab)
        await session.flush()
    else:
        lab.name = name
        lab.capacity = capacity
        lab.is_active = True
    existing_caps = (
        (await session.execute(select(LabCapability).where(LabCapability.lab_id == lab.id)))
        .scalars()
        .all()
    )
    existing_items = {c.experiment_item for c in existing_caps}
    for item in caps:
        if item not in existing_items:
            session.add(LabCapability(lab_id=lab.id, experiment_item=item))
    return lab


async def _upsert_machine(session: AsyncSession, spec: dict) -> None:
    existing = (
        await session.execute(select(Machine).where(Machine.machine_id == spec["machine_id"]))
    ).scalar_one_or_none()
    if existing:
        for k, v in spec.items():
            setattr(existing, k, v)
        return
    session.add(Machine(**spec))
    await session.flush()


async def _upsert_recipe(session: AsyncSession, spec: dict) -> None:
    existing = (
        await session.execute(select(Recipe).where(Recipe.recipe_id == spec["recipe_id"]))
    ).scalar_one_or_none()
    if existing:
        for k, v in spec.items():
            setattr(existing, k, v)
        return
    session.add(Recipe(**spec))
    await session.flush()


async def _upsert_order(
    session: AsyncSession,
    order_no: str,
    status: str,
    created_at: datetime,
    lab_code: str,
    experiment_item: str,
) -> OrderModel:
    """Order + a single matching OrderItemModel so OrderItemModel.lab_id-based
    scoping (kpi_new_orders / kpi_pending_approval / triage_pending_approvals)
    sees the row.
    """
    order = (
        await session.execute(select(OrderModel).where(OrderModel.order_no == order_no))
    ).scalar_one_or_none()
    if order is None:
        order = OrderModel(
            order_no=order_no,
            applicant_id="demo-user",
            department_id="DEPT-RD",
            apply_date=created_at,
            status=status,
            priority="normal",
            total_items=1,
        )
        session.add(order)
        await session.flush()
    else:
        order.status = status
        order.apply_date = created_at
    # Force the created_at into the rolling 24h window (default would be "now"
    # and we want the row to also light up sparkline buckets earlier in the
    # window). updated_at follows along.
    order.created_at = created_at
    order.updated_at = created_at

    # OrderItem — one per order, with lab_id (the lab code) so KPI / triage
    # / hourly-bucket queries find it under the right lab.
    item = (
        await session.execute(
            select(OrderItemModel).where(OrderItemModel.order_id == order.id).limit(1)
        )
    ).scalar_one_or_none()
    item_fields = {
        "order_id": order.id,
        "sample_id": f"{order_no}-S1",
        "sample_name": f"DEMO 樣品 {order_no[-3:]}",
        "lab_id": lab_code,
        "experiment_id": experiment_item,
        "status": "draft",
    }
    if item is None:
        session.add(OrderItemModel(**item_fields))
    else:
        for k, v in item_fields.items():
            setattr(item, k, v)
    await session.flush()
    return order


async def _ensure_sample(
    session: AsyncSession,
    sample_no: str,
    order_no: str,
    sample_name: str,
    experiment_item: str,
) -> uuid.UUID:
    """B's samples table has no ORM model — use raw SQL like seed_experiments."""
    existing = (
        await session.execute(
            text("SELECT id FROM samples WHERE sample_no = :sn"), {"sn": sample_no}
        )
    ).first()
    if existing:
        return existing[0]
    result = await session.execute(
        text(
            "INSERT INTO samples (sample_no, order_no, sample_name, experiment_item, status) "
            "VALUES (:sn, :on, :nm, :ei, 'received') RETURNING id"
        ),
        {"sn": sample_no, "on": order_no, "nm": sample_name, "ei": experiment_item},
    )
    await session.flush()
    return result.scalar_one()


async def _upsert_wip(session: AsyncSession, spec: dict) -> Wip:
    """Upsert a Wip + backing sample + WipExecution side row.

    ``spec`` keys: wip_no, order_no, lab_code, lab_name, experiment_item,
    status (DB CHECK vocab string), progress, started_at, completed_at,
    terminated_at, abort_reason, machine_id, recipe, operator,
    exec_status_enum (WipStatus member).
    """
    wip_no = spec["wip_no"]
    sample_no = f"DEMO-SMP-{wip_no.split('-')[-1]}-{spec['order_no'].split('-')[-1]}"
    sample_id = await _ensure_sample(
        session,
        sample_no,
        spec["order_no"],
        f"DEMO 樣品 {wip_no}",
        spec["experiment_item"],
    )

    wip = (await session.execute(select(Wip).where(Wip.wip_no == wip_no))).scalar_one_or_none()
    wip_fields = {
        "wip_no": wip_no,
        "sample_id": sample_id,
        "order_no": spec["order_no"],
        "lab_name": spec["lab_name"],
        "experiment_item": spec["experiment_item"],
        "priority": spec.get("priority", "normal"),
        "status": spec["status"],
        "progress": spec.get("progress", 0),
        "started_at": spec.get("started_at"),
        "completed_at": spec.get("completed_at"),
        "terminated_at": spec.get("terminated_at"),
    }
    if wip is None:
        wip = Wip(**wip_fields)
        session.add(wip)
        await session.flush()
    else:
        for k, v in wip_fields.items():
            setattr(wip, k, v)
        await session.flush()

    # WipExecution side row (D-owned). For waiting_schedule/scheduled buckets
    # the exec_status_enum may be None — skip the side row to mirror reality.
    exec_enum = spec.get("exec_status_enum")
    if exec_enum is not None:
        exec_row = await session.get(WipExecution, wip_no)
        exec_fields = {
            "exec_status": exec_enum.value,
            "machine_id": spec.get("machine_id"),
            "recipe": spec.get("recipe"),
            "operator": spec.get("operator"),
            "check_in_at": spec.get("started_at"),
            "check_out_at": spec.get("completed_at"),
            "result_note": spec.get("result_note"),
            "data_verified": spec.get("data_verified", False),
            "abort_status": spec.get("abort_status"),
            "abort_reason": spec.get("abort_reason"),
            "abort_by": spec.get("abort_by"),
            "abort_requested_at": spec.get("abort_requested_at"),
        }
        if exec_row is None:
            session.add(WipExecution(wip_no=wip_no, **exec_fields))
        else:
            for k, v in exec_fields.items():
                setattr(exec_row, k, v)
        await session.flush()
    return wip


async def _upsert_report(
    session: AsyncSession,
    report_id: str,
    order_no: str,
    wip_no: str,
    title: str,
    created_at: datetime,
    created_by: str,
) -> None:
    report = (
        await session.execute(select(Report).where(Report.report_id == report_id))
    ).scalar_one_or_none()
    returned_zh = REPORT_ZH[ReportStatus.RETURNED]
    fields = {
        "order_id": order_no,
        "wip_id": wip_no,
        "title": title,
        "summary": "DEMO 摘要",
        "conclusion": "DEMO 結論：合格。",
        "status": returned_zh,
        "created_at": created_at,
        "created_by": created_by,
    }
    if report is None:
        report = Report(report_id=report_id, **fields)
        session.add(report)
        await session.flush()
        # Single RETURNED version row.
        session.add(
            ReportVersion(
                report_id=report_id,
                version=1,
                status=returned_zh,
                actor=created_by,
                note="DEMO 已回傳",
            )
        )
        await session.flush()
    else:
        for k, v in fields.items():
            setattr(report, k, v)
        await session.flush()


async def _upsert_issue(
    session: AsyncSession,
    target_id: str,
    lab_id: uuid.UUID,
    title: str,
    severity: Severity,
    status: IssueStatus,
    escalation_level: int,
    updated_at: datetime,
    assigned_to: uuid.UUID | None,
) -> Issue:
    """Idempotent by ``target_id`` (we use DEMO-ISSUE-NN as the target_id so
    re-runs hit the same row)."""
    issue = (
        await session.execute(
            select(Issue).where(Issue.target_id == target_id, Issue.target_type == "demo")
        )
    ).scalar_one_or_none()
    fields = {
        "type": IssueType.ABNORMAL.value,
        "target_type": "demo",
        "target_id": target_id,
        "lab_id": lab_id,
        "title": title,
        "description": "DEMO 異常 — 由 seed_dashboard_demo 產生。",
        "severity": severity.value,
        "status": status.value,
        "assigned_to": assigned_to,
        "escalation_level": escalation_level,
        "created_at": updated_at - timedelta(hours=1),
        "updated_at": updated_at,
    }
    if issue is None:
        issue = Issue(**fields)
        session.add(issue)
        await session.flush()
    else:
        for k, v in fields.items():
            setattr(issue, k, v)
        await session.flush()
    return issue


async def _upsert_notification(
    session: AsyncSession,
    *,
    recipient_id: uuid.UUID,
    lab_id: uuid.UUID,
    issue_id: uuid.UUID,
    title: str,
    severity: Severity,
    created_at: datetime,
) -> None:
    """Idempotent on (recipient_id, source_type, source_id) — the demo's
    natural key for a notification."""
    source_id_str = str(issue_id)
    existing = (
        await session.execute(
            select(Notification).where(
                Notification.recipient_id == recipient_id,
                Notification.source_type == "issue",
                Notification.source_id == source_id_str,
            )
        )
    ).scalar_one_or_none()
    fields = {
        "recipient_id": recipient_id,
        "lab_id": lab_id,
        "source_type": "issue",
        "source_id": source_id_str,
        "title": title,
        "body": "DEMO 通知，請進儀表板確認。",
        "severity": severity.value,
        "channel": NotificationChannel.IN_APP.value,
        "status": NotificationStatus.UNREAD.value,
        "created_at": created_at,
        "updated_at": created_at,
    }
    if existing is None:
        session.add(Notification(**fields))
    else:
        for k, v in fields.items():
            setattr(existing, k, v)
    await session.flush()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def _run(session: AsyncSession) -> dict[str, int]:
    counts: dict[str, int] = {
        "labs": 0,
        "machines": 0,
        "recipes": 0,
        "orders": 0,
        "wips": 0,
        "reports": 0,
        "issues": 0,
        "notifications": 0,
    }

    # ---- Labs --------------------------------------------------------------
    for code, name, capacity, caps in DEMO_LABS:
        await _upsert_lab(session, code, name, capacity, caps)
        counts["labs"] += 1

    # Resolve lab_code -> (id, display_name) for downstream rows.
    lab_rows = (await session.execute(select(Lab.code, Lab.id, Lab.name))).all()
    lab_id_by_code: dict[str, uuid.UUID] = {r[0]: r[1] for r in lab_rows}
    lab_name_by_code: dict[str, str] = {r[0]: r[2] for r in lab_rows}

    # ---- Machines + Recipes -----------------------------------------------
    for spec in DEMO_MACHINES:
        await _upsert_machine(session, spec)
        counts["machines"] += 1
    for spec in DEMO_RECIPES:
        await _upsert_recipe(session, spec)
        counts["recipes"] += 1

    # ---- Orders ------------------------------------------------------------
    # Build order_no -> (lab_code, experiment_item, status, created_at) plan.
    # 20 orders total. Spread created_at across 24h so hourly_buckets_new_orders
    # has multiple non-zero buckets.
    order_specs: list[tuple[str, str, str, str, datetime]] = []
    order_idx = 0
    order_ts_list = _spread_24h(20, naive=False, max_hours_back=23.0)
    for status_value, count in ORDER_COUNTS.items():
        for _ in range(count):
            lab_code = LAB_CODES_FOR_WIPS[order_idx % len(LAB_CODES_FOR_WIPS)]
            experiment_item = RNG.choice(LAB_EXPERIMENT_ITEMS[lab_code])
            order_no = f"DEMO-WO-{order_idx + 1:03d}"
            order_specs.append(
                (order_no, status_value, lab_code, experiment_item, order_ts_list[order_idx])
            )
            order_idx += 1

    order_by_no: dict[str, OrderModel] = {}
    for order_no, status, lab_code, experiment_item, created_at in order_specs:
        order = await _upsert_order(
            session, order_no, status, created_at, lab_code, experiment_item
        )
        order_by_no[order_no] = order
        counts["orders"] += 1

    # ---- WIPs --------------------------------------------------------------
    # Bucket plan: 6 + 4 + 8 + 5 + 4 + 2 = 29 WIPs (brief said ~30).
    # We point each WIP at an order from the in_progress / waiting_pickup
    # / pending_approval pools as appropriate.

    # Index orders by status so we can pick the right kind for each bucket.
    orders_by_status: dict[str, list[OrderModel]] = {}
    for o in order_by_no.values():
        orders_by_status.setdefault(o.status, []).append(o)

    in_progress_orders = orders_by_status.get(OrderStatus.IN_PROGRESS.value, [])
    waiting_pickup_orders = orders_by_status.get(OrderStatus.WAITING_PICKUP.value, [])
    completed_orders = orders_by_status.get(OrderStatus.COMPLETED.value, [])

    wip_idx = 0
    completion_ts = _spread_24h(20, naive=True, max_hours_back=22.0)
    completion_cursor = 0

    def next_wip_no() -> str:
        nonlocal wip_idx
        wip_idx += 1
        return f"DEMO-WIP-{wip_idx:03d}"

    def pick_order(pool: list[OrderModel]) -> OrderModel:
        # Round-robin over the pool so each order has roughly even WIP count.
        return pool[(wip_idx) % len(pool)] if pool else next(iter(order_by_no.values()))

    # Bucket A: waiting_dispatch (6) — wips.status=waiting_schedule, NO Dispatch
    # row, point at IN_PROGRESS orders. exec_status omitted (no side row).
    for i in range(6):
        order = pick_order(in_progress_orders)
        lab_code = LAB_CODES_FOR_WIPS[i % len(LAB_CODES_FOR_WIPS)]
        await _upsert_wip(
            session,
            {
                "wip_no": next_wip_no(),
                "order_no": order.order_no,
                "lab_code": lab_code,
                "lab_name": lab_name_by_code[lab_code],
                "experiment_item": RNG.choice(LAB_EXPERIMENT_ITEMS[lab_code]),
                "status": "waiting_schedule",
                "progress": 0,
            },
        )
        counts["wips"] += 1

    # Bucket B: dispatched (4) — wips.status=scheduled.
    from app.common.enums import WipStatus  # local import; enum used only here

    for i in range(4):
        order = pick_order(in_progress_orders)
        lab_code = LAB_CODES_FOR_WIPS[(i + 1) % len(LAB_CODES_FOR_WIPS)]
        await _upsert_wip(
            session,
            {
                "wip_no": next_wip_no(),
                "order_no": order.order_no,
                "lab_code": lab_code,
                "lab_name": lab_name_by_code[lab_code],
                "experiment_item": RNG.choice(LAB_EXPERIMENT_ITEMS[lab_code]),
                "status": "scheduled",
                "progress": 5,
                "exec_status_enum": WipStatus.WAITING_LOAD,
                "machine_id": None,
                "operator": "DEMO 工程師",
            },
        )
        counts["wips"] += 1

    # Bucket C: in_progress (8) — 7 running + 1 paused.
    for i in range(8):
        order = pick_order(in_progress_orders)
        lab_code = LAB_CODES_FOR_WIPS[(i + 2) % len(LAB_CODES_FOR_WIPS)]
        is_paused = i == 7
        await _upsert_wip(
            session,
            {
                "wip_no": next_wip_no(),
                "order_no": order.order_no,
                "lab_code": lab_code,
                "lab_name": lab_name_by_code[lab_code],
                "experiment_item": RNG.choice(LAB_EXPERIMENT_ITEMS[lab_code]),
                "status": "paused" if is_paused else "running",
                "progress": 30 + i * 5,
                "started_at": _jitter_hours_ago(4 + i, naive=True),
                "exec_status_enum": WipStatus.RUNNING,
                "operator": "DEMO 工程師",
            },
        )
        counts["wips"] += 1

    # Bucket D: awaiting_handoff (5) — completed + RETURNED report +
    # order NOT in waiting_pickup/closed. Use in_progress_orders.
    for i in range(5):
        order = pick_order(in_progress_orders)
        lab_code = LAB_CODES_FOR_WIPS[(i + 3) % len(LAB_CODES_FOR_WIPS)]
        wip_no = next_wip_no()
        completed_at = completion_ts[completion_cursor]
        completion_cursor += 1
        await _upsert_wip(
            session,
            {
                "wip_no": wip_no,
                "order_no": order.order_no,
                "lab_code": lab_code,
                "lab_name": lab_name_by_code[lab_code],
                "experiment_item": RNG.choice(LAB_EXPERIMENT_ITEMS[lab_code]),
                "status": "completed",
                "progress": 100,
                "started_at": completed_at - timedelta(hours=3),
                "completed_at": completed_at,
                "exec_status_enum": WipStatus.COMPLETED,
                "operator": "DEMO 工程師",
                "result_note": "DEMO 結果合格",
                "data_verified": True,
            },
        )
        # Report — RETURNED, created_at sits inside the rolling 24h so it
        # bumps kpi_returned_today and hourly_buckets_returned.
        await _upsert_report(
            session,
            report_id=f"DEMO-RPT-{wip_no.split('-')[-1]}",
            order_no=order.order_no,
            wip_no=wip_no,
            title=f"DEMO 報告 - {wip_no}",
            created_at=completed_at + timedelta(minutes=10),
            created_by="DEMO 工程師",
        )
        counts["wips"] += 1
        counts["reports"] += 1

    # Bucket E: done (4) — completed + RETURNED + order in waiting_pickup.
    for i in range(4):
        order = pick_order(waiting_pickup_orders or in_progress_orders)
        lab_code = LAB_CODES_FOR_WIPS[(i + 4) % len(LAB_CODES_FOR_WIPS)]
        wip_no = next_wip_no()
        completed_at = completion_ts[completion_cursor]
        completion_cursor += 1
        await _upsert_wip(
            session,
            {
                "wip_no": wip_no,
                "order_no": order.order_no,
                "lab_code": lab_code,
                "lab_name": lab_name_by_code[lab_code],
                "experiment_item": RNG.choice(LAB_EXPERIMENT_ITEMS[lab_code]),
                "status": "completed",
                "progress": 100,
                "started_at": completed_at - timedelta(hours=4),
                "completed_at": completed_at,
                "exec_status_enum": WipStatus.COMPLETED,
                "operator": "DEMO 工程師",
                "result_note": "DEMO 結果合格 (待取件)",
                "data_verified": True,
            },
        )
        await _upsert_report(
            session,
            report_id=f"DEMO-RPT-{wip_no.split('-')[-1]}",
            order_no=order.order_no,
            wip_no=wip_no,
            title=f"DEMO 報告 - {wip_no}",
            created_at=completed_at + timedelta(minutes=15),
            created_by="DEMO 工程師",
        )
        counts["wips"] += 1
        counts["reports"] += 1

    # Bucket F: terminated (2). exec_status TERMINATED + abort_requested_at.
    for i in range(2):
        order = pick_order(in_progress_orders)
        lab_code = LAB_CODES_FOR_WIPS[(i + 1) % len(LAB_CODES_FOR_WIPS)]
        terminated_at = _jitter_hours_ago(2 + i * 5, naive=True)
        await _upsert_wip(
            session,
            {
                "wip_no": next_wip_no(),
                "order_no": order.order_no,
                "lab_code": lab_code,
                "lab_name": lab_name_by_code[lab_code],
                "experiment_item": RNG.choice(LAB_EXPERIMENT_ITEMS[lab_code]),
                "status": "terminated",
                "progress": 40,
                "started_at": terminated_at - timedelta(hours=2),
                "terminated_at": terminated_at,
                "exec_status_enum": WipStatus.TERMINATED,
                "operator": "DEMO 工程師",
                "abort_status": "已終止",
                "abort_reason": "DEMO 機台異常觸發中止",
                "abort_by": "DEMO 工程師",
                "abort_requested_at": terminated_at,
            },
        )
        counts["wips"] += 1

    # Extra COMPLETED-today WIPs purely to bump the "completed" KPI without
    # filling another bucket. These are also "completed + RETURNED + order
    # WAITING_PICKUP" so they fall in the done bucket alongside Bucket E.
    # We piggy-back on completed_orders so the orders are also "completed
    # today" — bumps the IN_PROGRESS pipeline less but reflects reality
    # (an order moves COMPLETED before WAITING_PICKUP).
    for i in range(len(completed_orders)):
        order = completed_orders[i]
        lab_code = LAB_CODES_FOR_WIPS[i % len(LAB_CODES_FOR_WIPS)]
        wip_no = next_wip_no()
        completed_at = completion_ts[completion_cursor % len(completion_ts)]
        completion_cursor += 1
        await _upsert_wip(
            session,
            {
                "wip_no": wip_no,
                "order_no": order.order_no,
                "lab_code": lab_code,
                "lab_name": lab_name_by_code[lab_code],
                "experiment_item": RNG.choice(LAB_EXPERIMENT_ITEMS[lab_code]),
                "status": "completed",
                "progress": 100,
                "started_at": completed_at - timedelta(hours=2),
                "completed_at": completed_at,
                "exec_status_enum": WipStatus.COMPLETED,
                "operator": "DEMO 工程師",
                "data_verified": True,
            },
        )
        await _upsert_report(
            session,
            report_id=f"DEMO-RPT-{wip_no.split('-')[-1]}",
            order_no=order.order_no,
            wip_no=wip_no,
            title=f"DEMO 完工報告 - {wip_no}",
            created_at=completed_at + timedelta(minutes=5),
            created_by="DEMO 工程師",
        )
        counts["wips"] += 1
        counts["reports"] += 1

    # ---- Issues + Notifications -------------------------------------------
    # Resolve a recipient pool: every active supervisor + the general_sup +
    # at least one engineer. They all get the unread notifications.
    recipient_rows = (
        await session.execute(
            select(User.id, User.lab_id).where(
                User.email.in_(
                    [
                        "supervisor@example.com",
                        "supervisor2@example.com",
                        "supervisor3@example.com",
                        "director@example.com",
                        "engineer@example.com",
                    ]
                )
            )
        )
    ).all()
    recipients: list[tuple[uuid.UUID, uuid.UUID | None]] = [(r[0], r[1]) for r in recipient_rows]

    for i, (severity, status, level, hours_ago) in enumerate(ISSUE_SPECS):
        # Round-robin a lab so issues span all 5 — keeps lab_leaderboard's
        # open_high_critical_issues column non-zero everywhere.
        lab_code = LAB_CODES_FOR_WIPS[i % len(LAB_CODES_FOR_WIPS)]
        lab_id = lab_id_by_code[lab_code]
        target_id = f"DEMO-ISSUE-{i + 1:02d}"
        title = f"DEMO {severity.value} 異常 #{i + 1} ({lab_code})"
        updated_at = _jitter_hours_ago(hours_ago, naive=False)
        issue = await _upsert_issue(
            session,
            target_id=target_id,
            lab_id=lab_id,
            title=title,
            severity=severity,
            status=status,
            escalation_level=level,
            updated_at=updated_at,
            assigned_to=None,
        )
        counts["issues"] += 1

        # Notifications: send to every recipient who has a matching lab
        # (or every recipient if they have no lab — director / sysadmin).
        # We deliberately do NOT mark any as READ — the dashboard's triage
        # widget surfaces unack-ed issues so we want them all visible.
        for recipient_id, recipient_lab_id in recipients:
            if recipient_lab_id is not None and recipient_lab_id != lab_id:
                # Skip lab-scoped supervisors that aren't in this issue's lab.
                continue
            await _upsert_notification(
                session,
                recipient_id=recipient_id,
                lab_id=lab_id,
                issue_id=issue.id,
                title=title,
                severity=severity,
                created_at=updated_at,
            )
            counts["notifications"] += 1

    return counts


async def main() -> None:
    async with AsyncSessionLocal() as session:
        counts = await _run(session)
        await session.commit()

    sys.stdout.write("Dashboard demo seed complete.\n")
    for k, v in counts.items():
        sys.stdout.write(f"  {k:>13}: {v}\n")
    sys.stdout.write(
        "Re-run safe — every row is upserted by natural key "
        "(DEMO-* prefixes; D-* for machine/recipe ids).\n"
    )


if __name__ == "__main__":
    asyncio.run(main())

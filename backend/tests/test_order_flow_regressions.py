"""Regression tests for the end-to-end order-flow bugs surfaced 2026-05-29.

Three independent bugs walked through together — each test pins one of them.

1. ``Wip.completed_at`` was NULL after ``confirm_result`` flipped status to
   ``completed``. The dashboard's "完工 today" KPI and every other rolling-24h
   window that filters on ``Wip.completed_at`` silently dropped the row, even
   though ``Wip.status == 'completed'``. The fix stamps ``completed_at`` in
   the service at the same call site that calls ``_set_status(..., COMPLETED)``.

2. The dashboard's ``awaiting_handoff`` / ``done`` pipeline buckets required
   ``Report.status == '已回傳'``. A completed WIP whose report hadn't been
   published yet matched neither bucket and disappeared from the pipeline
   visualisation entirely. The fix drops the report-status condition: bucket
   transitions are now driven purely by ``OrderModel.status``.

3. ``ClosureService.close_order`` raised on "尚有樣品未取件" only when storage
   items existed AND not all were ``picked_up``. An order at ``waiting_pickup``
   with zero storage rows (no inbound has run) bypassed the guard and could
   be flipped to CLOSED before the user had actually picked anything up. The
   fix treats an empty ``items`` list as "not yet picked up" too.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.common.dependencies.lab_scope import LabScope
from app.common.enums import OrderStatus, WipStatus
from app.common.errors import ConflictError
from app.db.models import OrderModel, Wip, WipExecution
from app.modules.closures.repository import ClosureRepository
from app.modules.closures.service import ClosureService
from app.modules.dashboard.repository import DashboardRepository
from app.modules.experiment_runs.repository import ExperimentRunRepository
from app.modules.experiment_runs.service import ExperimentRunService

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _stub_sample_flow_advance(monkeypatch):
    """Short-circuit B's cross-owner sample-flow advance for these tests.

    ``ExperimentRunService.confirm_result`` calls ``_advance_sample_flow``
    after its first commit. That helper runs raw-SQL queries against B's
    ``samples`` table, which is migration-only and not part of
    ``Base.metadata`` — so the test DB (rebuilt from ``create_all``) doesn't
    have it. The query raises ``UndefinedTable`` and aborts the session's
    transaction, which then trips ``_publish_wip_pipeline_change``'s later
    SELECT against ``labs``.

    The bug under test is purely about ``Wip.completed_at`` being stamped
    on the first commit, before sample-flow advance — so neutralising the
    cross-owner call is the right scope for the regression. Production has
    the ``samples`` table and the helper continues to run.
    """

    async def _noop(*_args, **_kwargs):
        return None

    monkeypatch.setattr(ExperimentRunService, "_advance_sample_flow", _noop)


def _suite() -> str:
    return uuid.uuid4().hex[:8]


async def _seed_order(db_session, *, order_no: str, status: str) -> OrderModel:
    """Seed an OrderModel with the minimum fields the dashboard needs.

    ``OrderModel.created_at`` defaults to the server side; for windowed-query
    tests we override it explicitly to keep the row inside the trailing 24h
    window regardless of any clock drift in CI.
    """
    now = datetime.now(UTC)
    order = OrderModel(
        order_no=order_no,
        applicant_id="reg-applicant",
        department_id="DEPT-RD",
        apply_date=now,
        status=status,
        priority="normal",
        total_items=1,
        created_at=now,
    )
    db_session.add(order)
    await db_session.flush()
    return order


async def _seed_wip(
    db_session,
    *,
    wip_no: str,
    order_no: str,
    status: str,
    lab_name: str = "材料分析實驗室",
    completed_at: datetime | None = None,
) -> Wip:
    wip = Wip(
        wip_no=wip_no,
        sample_id=uuid.uuid4(),
        order_no=order_no,
        lab_name=lab_name,
        experiment_item="reg",
        priority="normal",
        status=status,
        progress=100 if status == "completed" else 0,
        completed_at=completed_at,
    )
    db_session.add(wip)
    await db_session.flush()
    return wip


# ---------------------------------------------------------------------------
# Issue 1a — ExperimentRunService.confirm_result stamps Wip.completed_at.
# ---------------------------------------------------------------------------


async def test_confirm_result_stamps_wip_completed_at(db_session) -> None:
    """After confirm_result flips a WIP to COMPLETED, ``Wip.completed_at`` must
    be non-NULL so the dashboard KPI "完工 today" picks it up.
    """
    suite = _suite()
    order_no = f"REG-OF1A-O-{suite}"
    wip_no = f"REG-OF1A-W-{suite}"

    await _seed_order(db_session, order_no=order_no, status=OrderStatus.IN_PROGRESS.value)
    await _seed_wip(db_session, wip_no=wip_no, order_no=order_no, status="running")
    # Seed an execution row at WAITING_CONFIRM with verified data — confirm_result's
    # only two gates.
    db_session.add(
        WipExecution(
            wip_no=wip_no,
            exec_status=WipStatus.WAITING_CONFIRM.value,
            data_verified=True,
        )
    )
    await db_session.commit()

    service = ExperimentRunService(ExperimentRunRepository(db_session), LabScope.system())
    await service.confirm_result(wip_no, operator="tester")

    db_session.expire_all()
    refreshed = await ExperimentRunRepository(db_session).get_wip(wip_no)
    assert refreshed is not None
    assert refreshed.status == "completed"
    assert (
        refreshed.completed_at is not None
    ), "Wip.completed_at must be stamped when confirm_result flips status to completed"


# Note: a direct end-to-end assertion against ``kpi_completed_today`` would
# couple this test to a separate pre-existing bug — ``ExperimentRunService``
# computes ``_now()`` via ``datetime.now()`` (local naive time, e.g. UTC+8 in
# CI) while ``DashboardRepository._now_naive()`` uses ``datetime.now(UTC)``
# stripped of tzinfo. The rolling-24h window measures past-UTC time, but
# ``completed_at`` is stamped at present-local time — which can fall outside
# the window on a non-UTC box. That timezone-mixing belongs in a separate
# fix; the regression for 1a is that ``Wip.completed_at`` is non-NULL after
# confirm_result (covered above).


# ---------------------------------------------------------------------------
# Issue 1b — pipeline awaiting_handoff/done no longer require Report.RETURNED.
# ---------------------------------------------------------------------------


async def test_pipeline_awaiting_handoff_includes_completed_wips_without_report(
    db_session,
) -> None:
    """A WIP at ``status=completed`` whose order is NOT in waiting_pickup/closed
    must land in the ``awaiting_handoff`` bucket even when no RETURNED report
    exists. Previously the bucket's EXISTS-clause on Report.status made the
    WIP disappear from every pipeline bucket between completion and report
    publish.
    """
    suite = _suite()
    order_no = f"REG-OF1B-O-{suite}"
    wip_no = f"REG-OF1B-W-{suite}"
    lab_name = "材料分析實驗室"

    await _seed_order(db_session, order_no=order_no, status=OrderStatus.IN_PROGRESS.value)
    await _seed_wip(
        db_session,
        wip_no=wip_no,
        order_no=order_no,
        status="completed",
        lab_name=lab_name,
        completed_at=datetime.now(UTC).replace(tzinfo=None),
    )
    await db_session.commit()

    repo = DashboardRepository(db_session)
    counts = await repo.wip_pipeline_counts(lab_codes=["LAB-A"])
    assert (
        counts["awaiting_handoff"][0] >= 1
    ), "a completed WIP must surface in awaiting_handoff before any report is RETURNED"


async def test_pipeline_done_includes_completed_wips_without_report_when_order_waiting_pickup(
    db_session,
) -> None:
    """And the mirror case: ``OrderStatus.WAITING_PICKUP`` → bucket ``done``.

    Drops the Report.RETURNED gate symmetrically so the WIP transitions
    awaiting_handoff → done purely on the order status flipping to
    waiting_pickup.
    """
    suite = _suite()
    order_no = f"REG-OF1B2-O-{suite}"
    wip_no = f"REG-OF1B2-W-{suite}"
    lab_name = "材料分析實驗室"

    await _seed_order(db_session, order_no=order_no, status=OrderStatus.WAITING_PICKUP.value)
    await _seed_wip(
        db_session,
        wip_no=wip_no,
        order_no=order_no,
        status="completed",
        lab_name=lab_name,
        completed_at=datetime.now(UTC).replace(tzinfo=None),
    )
    await db_session.commit()

    repo = DashboardRepository(db_session)
    counts = await repo.wip_pipeline_counts(lab_codes=["LAB-A"])
    assert counts["done"][0] >= 1


# ---------------------------------------------------------------------------
# Issue 2 — close_order rejects empty storage items.
# ---------------------------------------------------------------------------


async def test_close_order_rejects_when_no_storage_items(db_session) -> None:
    """An order at WAITING_PICKUP with NO ``storage`` rows must NOT be
    closeable — that means the operator never recorded an outbound (出庫取件)
    so the user hasn't actually picked anything up.

    Previously ``if items and not all(...)`` short-circuited on empty
    ``items`` and let close_order succeed.
    """
    suite = _suite()
    order_no = f"REG-OF2-O-{suite}"
    await _seed_order(db_session, order_no=order_no, status=OrderStatus.WAITING_PICKUP.value)
    await db_session.commit()

    service = ClosureService(ClosureRepository(db_session), LabScope.system())
    with pytest.raises(ConflictError, match="尚有樣品未取件"):
        await service.close_order(order_no, operator="tester")

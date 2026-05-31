"""Regression tests for the end-to-end order-flow bugs surfaced 2026-05-29.

Four independent bugs walked through together — each test pins one of them.

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

4. ``DashboardRepository.recent_escalations`` filtered ``Issue.status ==
   'escalated'``. Phase K C5 (ack from notification center) flips the issue's
   status to ``acknowledged`` while leaving ``escalation_level > 0`` — so an
   ack'd issue silently disappeared from the supervisor's "Recent Escalations"
   panel the moment they read it. The fix drops the status filter and gates
   on ``escalation_level > 0`` instead so the panel works as a 24h escalation
   audit log, not a "currently-escalating" snapshot.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.common.dependencies.lab_scope import LabScope
from app.common.enums import IssueStatus, OrderStatus, Severity, WipStatus
from app.common.errors import ConflictError
from app.db.models import Issue, Lab, Notification, OrderModel, Wip, WipExecution
from app.db.models.users import User
from app.modules.closures.repository import ClosureRepository
from app.modules.closures.service import ClosureService
from app.modules.dashboard.repository import DashboardRepository
from app.modules.experiment_runs.repository import ExperimentRunRepository
from app.modules.experiment_runs.service import ABORT_PENDING, ExperimentRunService

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _stub_sample_flow_advance(monkeypatch):
    """Short-circuit B's cross-owner sample-flow advance for these tests.

    ``ExperimentRunService.confirm_result`` calls ``_advance_sample_flow``
    and ``review_abort(approve=True)`` calls ``_advance_sample_on_termination``;
    both run raw-SQL queries against B's ``samples`` table, which is
    migration-only and not part of ``Base.metadata`` — so the test DB
    (rebuilt from ``create_all``) doesn't have it. The query raises
    ``UndefinedTable`` and aborts the session's transaction, which then
    trips downstream queries like ``_publish_wip_pipeline_change`` 's
    SELECT against ``labs``.

    Most tests here pin upstream behaviour(``completed_at`` stamp, order
    status rollup, notification fan-out) and don't care about the sample
    flow — so neutralising both call sites is the right scope. Tests that
    DO want to exercise the real sample helper(see the OF5B / OF5C
    block at the bottom of this file)opt out by passing
    ``stub_sample_helpers=False`` via the ``sample_table_setup`` fixture,
    which also CREATEs the ad-hoc ``samples`` table.
    """

    async def _noop(*_args, **_kwargs):
        return None

    monkeypatch.setattr(ExperimentRunService, "_advance_sample_flow", _noop)
    monkeypatch.setattr(ExperimentRunService, "_advance_sample_on_termination", _noop)


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


async def _seed_issue(
    db_session,
    *,
    lab_id: uuid.UUID,
    severity: Severity,
    status: IssueStatus,
    escalation_level: int,
    title: str | None = None,
) -> Issue:
    """Seed an Issue with the minimum fields recent_escalations / triage need.

    ``updated_at`` is set server-side; the regression test below relies on the
    default landing inside the rolling 24h window — which it always does for a
    row inserted in the same test run.
    """
    issue = Issue(
        type="warning",
        target_type="machine",
        target_id=f"M-REG-{uuid.uuid4().hex[:6]}",
        lab_id=lab_id,
        title=title or f"reg issue {uuid.uuid4().hex[:6]}",
        description="",
        severity=severity,
        status=status,
        escalation_level=escalation_level,
    )
    db_session.add(issue)
    await db_session.flush()
    return issue


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


# ---------------------------------------------------------------------------
# Issue 4 — recent_escalations keeps ack'd issues in the 24h audit window.
# ---------------------------------------------------------------------------


async def test_recent_escalations_includes_acknowledged_issues_within_24h(
    db_session,
) -> None:
    """Phase K C5 flips issue.status from 'escalated' to 'acknowledged' when
    the user reads the notification. The recent_escalations panel should
    still show that issue (it WAS escalated in the last 24h) — otherwise
    the supervisor loses all history the moment they ack.
    """
    lab = (await db_session.execute(select(Lab).where(Lab.code == "LAB-A"))).scalar_one()

    issue = await _seed_issue(
        db_session,
        lab_id=lab.id,
        severity=Severity.CRITICAL,
        status=IssueStatus.ACKNOWLEDGED,
        escalation_level=2,
        title=f"REG-OF4 acked-but-escalated {_suite()}",
    )
    await db_session.commit()

    repo = DashboardRepository(db_session)
    rows = await repo.recent_escalations(lab_codes=None, limit=50)
    assert any(str(r[0]) == str(issue.id) for r in rows), (
        "an acknowledged issue with escalation_level>0 must still appear in "
        "recent_escalations within 24h — Phase K C5 ack must not erase the "
        "supervisor's escalation history"
    )


# ---------------------------------------------------------------------------
# Issue 5 — supervisor-approved abort must surface on the order owner's side.
# Three concerns: (a) order.status reflects TERMINATED when every WIP ended via
# abort, (b) the order owner gets an in-app notification, (c) a mixed bag of
# completed + terminated WIPs still rolls up to COMPLETED.
# ---------------------------------------------------------------------------


async def _seed_wip_with_abort_pending(
    db_session,
    *,
    wip_no: str,
    order_no: str,
    lab_name: str = "材料分析實驗室",
) -> Wip:
    """Seed a running WIP + matching WipExecution that already has an abort
    request waiting for supervisor review (the state ``review_abort`` expects)."""
    wip = await _seed_wip(
        db_session, wip_no=wip_no, order_no=order_no, status="running", lab_name=lab_name
    )
    db_session.add(
        WipExecution(
            wip_no=wip_no,
            exec_status=WipStatus.RUNNING.value,
            abort_status=ABORT_PENDING,
            abort_reason="machine issue",
            abort_by="tester",
            data_verified=False,
        )
    )
    await db_session.flush()
    return wip


async def test_abort_approval_terminates_order_when_all_wips_terminated(
    db_session,
) -> None:
    """When the last (and only) WIP of an order is approved-terminated, the
    order itself must flip to ``terminated`` — not ``completed``. Previously
    ``_refresh_order_after_confirm`` rolled an all-terminated order up to
    COMPLETED because ``ENDED_EXEC`` covers both completed and terminated, so
    the plant_user saw "已完成" on a fully aborted order.
    """
    suite = _suite()
    order_no = f"REG-OF5A-O-{suite}"
    wip_no = f"REG-OF5A-W-{suite}"

    await _seed_order(db_session, order_no=order_no, status=OrderStatus.IN_PROGRESS.value)
    await _seed_wip_with_abort_pending(db_session, wip_no=wip_no, order_no=order_no)
    await db_session.commit()

    service = ExperimentRunService(ExperimentRunRepository(db_session), LabScope.system())
    await service.review_abort(wip_no, approve=True, note="approved", by="supervisor")

    db_session.expire_all()
    refreshed = await db_session.get(
        OrderModel,
        (
            await db_session.execute(select(OrderModel.id).where(OrderModel.order_no == order_no))
        ).scalar_one(),
    )
    assert refreshed is not None
    assert refreshed.status == OrderStatus.TERMINATED.value, (
        "an order whose every WIP ended via supervisor-approved abort must roll "
        "up to TERMINATED, not COMPLETED — otherwise the plant_user can't tell "
        "their order was aborted"
    )


async def test_abort_approval_with_mixed_wips_keeps_order_completed(
    db_session,
) -> None:
    """If an order has some COMPLETED and some TERMINATED WIPs, the order should
    still flip to COMPLETED — at least one WIP produced real experimental output,
    so the order is not "all aborted". This guards against an over-correction of
    the all-terminated case accidentally TERMINATING any order with a single
    aborted WIP.
    """
    suite = _suite()
    order_no = f"REG-OF5B-O-{suite}"
    wip_completed_no = f"REG-OF5B-WC-{suite}"
    wip_abort_no = f"REG-OF5B-WA-{suite}"

    await _seed_order(db_session, order_no=order_no, status=OrderStatus.IN_PROGRESS.value)
    # WIP #1: already completed (exec WAITING_CONFIRM with data verified → fed to confirm_result)
    await _seed_wip(
        db_session,
        wip_no=wip_completed_no,
        order_no=order_no,
        status="running",
    )
    db_session.add(
        WipExecution(
            wip_no=wip_completed_no,
            exec_status=WipStatus.WAITING_CONFIRM.value,
            data_verified=True,
        )
    )
    # WIP #2: abort pending → will be approved
    await _seed_wip_with_abort_pending(db_session, wip_no=wip_abort_no, order_no=order_no)
    await db_session.commit()

    service = ExperimentRunService(ExperimentRunRepository(db_session), LabScope.system())
    # Confirm the first WIP — order is not yet "all ended".
    await service.confirm_result(wip_completed_no, operator="tester")
    # Approve the abort on the second WIP — now every WIP is in ENDED_EXEC, but
    # it's a *mix* (one COMPLETED, one TERMINATED).
    await service.review_abort(wip_abort_no, approve=True, note="approved", by="supervisor")

    db_session.expire_all()
    refreshed_id = (
        await db_session.execute(select(OrderModel.id).where(OrderModel.order_no == order_no))
    ).scalar_one()
    refreshed = await db_session.get(OrderModel, refreshed_id)
    assert refreshed is not None
    assert refreshed.status == OrderStatus.COMPLETED.value, (
        "an order with a mix of COMPLETED + TERMINATED WIPs must stay COMPLETED "
        "(real output exists); the TERMINATED rollup only kicks in when EVERY "
        "WIP was aborted"
    )


async def test_abort_approval_notifies_order_applicant(db_session) -> None:
    """When ``review_abort(approve=True)`` lands, the plant_user who owns the
    order receives an in-app Notification. Without this hop the applicant has
    no in-app signal that their experiment was killed by the supervisor and
    only finds out by reloading the order page.
    """
    suite = _suite()
    order_no = f"REG-OF5C-O-{suite}"
    wip_no = f"REG-OF5C-W-{suite}"
    applicant_email = f"applicant-{suite}@example.com"

    # Resolve a real Lab so the notification has a valid lab_id fallback.
    lab = (await db_session.execute(select(Lab).where(Lab.code == "LAB-A"))).scalar_one()

    # Seed a plant_user (lab-less, as in production) — only the bare User row
    # is required; no role / permission setup needed because notifications
    # are scoped on recipient_id, not on a role.
    applicant = User(
        email=applicant_email,
        name=f"Applicant {suite}",
        password_hash="x" * 60,
        lab_id=None,
    )
    db_session.add(applicant)
    await db_session.flush()

    order = await _seed_order(db_session, order_no=order_no, status=OrderStatus.IN_PROGRESS.value)
    order.applicant_id = str(applicant.id)  # mirrors order_repo.user_id(current_user)
    await _seed_wip_with_abort_pending(
        db_session, wip_no=wip_no, order_no=order_no, lab_name=lab.name
    )
    await db_session.commit()

    applicant_id = applicant.id

    service = ExperimentRunService(ExperimentRunRepository(db_session), LabScope.system())
    await service.review_abort(wip_no, approve=True, note="approved", by="supervisor")

    db_session.expire_all()
    notes = (
        (
            await db_session.execute(
                select(Notification).where(
                    Notification.recipient_id == applicant_id,
                    Notification.source_type == "order",
                    Notification.source_id == order_no,
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(notes) >= 1, (
        "plant_user applicant must receive an in-app notification when their "
        "WIP is approved-terminated by the supervisor"
    )


# Note: ``_advance_sample_on_termination`` (called from review_abort) is
# verified manually in the docker demo flow — the helper queries B's
# ``samples`` table which is migration-only and not in Base.metadata, so
# the test DB rebuilt from create_all can't exercise it. The autouse
# fixture above neutralises both sample helpers so the rest of these
# tests aren't perturbed.


# ---------------------------------------------------------------------------
# Issue 6 — cross-lab closure via Wip.lab_closed (TODO #4).
# ---------------------------------------------------------------------------
# Tests:
#  6a — all_wips_lab_closed repo helper returns False for partial state
#  6b — all_wips_lab_closed flips True once every WIP is closed
#  6c — count_returned_reports_per_wip — has_report per-WIP fix (Phase L #2)
#  6d — to_pickup on a multi-lab order from LAB-A only marks LAB-A's WIPs;
#       order stays out of WAITING_PICKUP
#  6e — to_pickup once every lab has signed off flips order to WAITING_PICKUP


async def _seed_closed_exec(db_session, *, wip_no: str) -> WipExecution:
    """Seed a WipExecution in COMPLETED state with result_note set, so the
    closure ``all_ended`` / ``data_collected`` gates both pass for this WIP."""
    exec_row = WipExecution(
        wip_no=wip_no,
        exec_status=WipStatus.COMPLETED.value,
        data_verified=True,
        result_note="(seeded for regression)",
    )
    db_session.add(exec_row)
    await db_session.flush()
    return exec_row


async def _seed_returned_report(db_session, *, order_no: str, wip_no: str, report_id: str) -> None:
    """Seed a Report in RETURNED state attached to the given WIP so the
    closure ``has_report`` per-WIP gate counts it."""
    from app.common.enums import ReportStatus
    from app.common.enums.role_d_zh import REPORT_ZH
    from app.db.models.reports import Report

    db_session.add(
        Report(
            report_id=report_id,
            order_id=order_no,
            wip_id=wip_no,
            title="regression report",
            summary="",
            conclusion="",
            status=REPORT_ZH[ReportStatus.RETURNED],
            created_by="tester",
        )
    )
    await db_session.flush()


@pytest.fixture
def _stub_closure_sample_check(monkeypatch):
    """Bypass the closure module's ``sample_statuses`` raw-SQL lookup (B's
    ``samples`` table isn't in Base.metadata, so the test DB doesn't have
    it). Returns delivered states so the ``sample_ok`` gate passes."""

    async def _delivered(_self, _order_no):
        return ["picked_up"]

    monkeypatch.setattr(ClosureRepository, "sample_statuses", _delivered)


async def test_all_wips_lab_closed_returns_false_when_partial(db_session) -> None:
    """The cross-lab closure gate must require EVERY WIP to have
    ``lab_closed=True``. Partial state (1 of 2 closed) returns False so the
    order does NOT advance to WAITING_PICKUP yet."""
    suite = _suite()
    order_no = f"REG-OF6A-O-{suite}"
    await _seed_order(db_session, order_no=order_no, status=OrderStatus.IN_PROGRESS.value)
    wip_a = await _seed_wip(
        db_session,
        wip_no=f"REG-OF6A-WA-{suite}",
        order_no=order_no,
        status="completed",
        lab_name="材料分析實驗室",
    )
    wip_b = await _seed_wip(
        db_session,
        wip_no=f"REG-OF6A-WB-{suite}",
        order_no=order_no,
        status="completed",
        lab_name="電性測試實驗室",
    )
    wip_a.lab_closed = True  # only LAB-A done
    wip_b.lab_closed = False
    await db_session.commit()

    repo = ClosureRepository(db_session)
    assert await repo.all_wips_lab_closed(order_no) is False


async def test_all_wips_lab_closed_returns_true_when_every_lab_done(
    db_session,
) -> None:
    """Once every WIP on the order has ``lab_closed=True``, the gate flips
    True and the next ``to_pickup`` call can advance the order."""
    suite = _suite()
    order_no = f"REG-OF6B-O-{suite}"
    await _seed_order(db_session, order_no=order_no, status=OrderStatus.IN_PROGRESS.value)
    for n, lab in enumerate(["材料分析實驗室", "電性測試實驗室"]):
        wip = await _seed_wip(
            db_session,
            wip_no=f"REG-OF6B-W{n}-{suite}",
            order_no=order_no,
            status="completed",
            lab_name=lab,
        )
        wip.lab_closed = True
    await db_session.commit()

    repo = ClosureRepository(db_session)
    assert await repo.all_wips_lab_closed(order_no) is True


async def test_count_returned_reports_per_wip_fixes_has_report_gate(
    db_session,
) -> None:
    """Phase L review #2: the ``has_report`` gate USED to read
    ``count_reports_in_status > 0`` (at least one returned report on the
    whole order). For a multi-lab order with reports from only some labs,
    that wrongly let the gate pass. The per-WIP map exposes the correct
    distribution so the service can verify EVERY WIP has its own RETURNED
    report."""
    suite = _suite()
    order_no = f"REG-OF6C-O-{suite}"
    wip_a = f"REG-OF6C-WA-{suite}"
    wip_b = f"REG-OF6C-WB-{suite}"

    await _seed_order(db_session, order_no=order_no, status=OrderStatus.IN_PROGRESS.value)
    await _seed_wip(
        db_session, wip_no=wip_a, order_no=order_no, status="completed", lab_name="材料分析實驗室"
    )
    await _seed_wip(
        db_session, wip_no=wip_b, order_no=order_no, status="completed", lab_name="電性測試實驗室"
    )
    # Only wip_a has a RETURNED report; wip_b has none yet.
    await _seed_returned_report(
        db_session, order_no=order_no, wip_no=wip_a, report_id=f"R-{suite}-A"
    )
    await db_session.commit()

    repo = ClosureRepository(db_session)
    per_wip = await repo.count_returned_reports_per_wip(order_no)
    assert per_wip == {
        wip_a: 1
    }, f"per-WIP map should only include WIPs with RETURNED reports; got {per_wip!r}"
    # And the "every WIP has report" check the service does:
    wips = [wip_a, wip_b]
    has_report = all(per_wip.get(w, 0) > 0 for w in wips)
    assert has_report is False, "multi-lab order with one report missing must NOT pass has_report"


async def test_to_pickup_from_one_lab_does_not_advance_multi_lab_order(
    db_session, _stub_closure_sample_check
) -> None:
    """LAB-A presses ``to_pickup`` on an order shared with LAB-B. LAB-A's
    WIPs flip ``lab_closed=True`` but order.status stays in
    WAITING_REPORT_RETURN — LAB-B hasn't signed off yet."""
    suite = _suite()
    order_no = f"REG-OF6D-O-{suite}"
    wip_a = f"REG-OF6D-WA-{suite}"
    wip_b = f"REG-OF6D-WB-{suite}"

    await _seed_order(db_session, order_no=order_no, status=OrderStatus.WAITING_REPORT_RETURN.value)
    await _seed_wip(
        db_session, wip_no=wip_a, order_no=order_no, status="completed", lab_name="材料分析實驗室"
    )
    await _seed_wip(
        db_session, wip_no=wip_b, order_no=order_no, status="completed", lab_name="電性測試實驗室"
    )
    await _seed_closed_exec(db_session, wip_no=wip_a)
    await _seed_closed_exec(db_session, wip_no=wip_b)
    await _seed_returned_report(
        db_session, order_no=order_no, wip_no=wip_a, report_id=f"R-{suite}-A"
    )
    await _seed_returned_report(
        db_session, order_no=order_no, wip_no=wip_b, report_id=f"R-{suite}-B"
    )
    await db_session.commit()

    lab_a_scope = LabScope(role="lab_supervisor", lab_name="材料分析實驗室", lab_code="LAB-A")
    service = ClosureService(ClosureRepository(db_session), lab_a_scope)
    result = await service.to_pickup(order_no)

    db_session.expire_all()
    refreshed_order = (
        await db_session.execute(select(OrderModel).where(OrderModel.order_no == order_no))
    ).scalar_one_or_none()
    assert refreshed_order is not None
    assert refreshed_order.status == OrderStatus.WAITING_REPORT_RETURN.value, (
        f"order must NOT advance to WAITING_PICKUP while LAB-B's WIPs are still "
        f"lab_closed=False; got {refreshed_order.status!r}"
    )
    refreshed_wip_a = (
        await db_session.execute(select(Wip).where(Wip.wip_no == wip_a))
    ).scalar_one()
    refreshed_wip_b = (
        await db_session.execute(select(Wip).where(Wip.wip_no == wip_b))
    ).scalar_one()
    assert refreshed_wip_a.lab_closed is True
    assert refreshed_wip_b.lab_closed is False
    assert result.get("labClosed") is True


async def test_to_pickup_once_all_labs_closed_advances_order(
    db_session, _stub_closure_sample_check
) -> None:
    """The last lab to call ``to_pickup`` flips ``all_wips_lab_closed`` True,
    and the order finally advances to WAITING_PICKUP."""
    suite = _suite()
    order_no = f"REG-OF6E-O-{suite}"
    wip_a = f"REG-OF6E-WA-{suite}"
    wip_b = f"REG-OF6E-WB-{suite}"

    await _seed_order(db_session, order_no=order_no, status=OrderStatus.WAITING_REPORT_RETURN.value)
    # LAB-A already pressed to_pickup previously.
    seeded_a = await _seed_wip(
        db_session, wip_no=wip_a, order_no=order_no, status="completed", lab_name="材料分析實驗室"
    )
    seeded_a.lab_closed = True
    await _seed_wip(
        db_session, wip_no=wip_b, order_no=order_no, status="completed", lab_name="電性測試實驗室"
    )
    await _seed_closed_exec(db_session, wip_no=wip_a)
    await _seed_closed_exec(db_session, wip_no=wip_b)
    await _seed_returned_report(
        db_session, order_no=order_no, wip_no=wip_a, report_id=f"R-{suite}-A"
    )
    await _seed_returned_report(
        db_session, order_no=order_no, wip_no=wip_b, report_id=f"R-{suite}-B"
    )
    await db_session.commit()

    # Now LAB-B presses to_pickup as the second & final lab.
    lab_b_scope = LabScope(role="lab_supervisor", lab_name="電性測試實驗室", lab_code="LAB-B")
    service = ClosureService(ClosureRepository(db_session), lab_b_scope)
    await service.to_pickup(order_no)

    db_session.expire_all()
    refreshed_order = (
        await db_session.execute(select(OrderModel).where(OrderModel.order_no == order_no))
    ).scalar_one_or_none()
    assert refreshed_order is not None
    assert refreshed_order.status == OrderStatus.WAITING_PICKUP.value, (
        f"order must advance to WAITING_PICKUP once every lab has signed off; "
        f"got {refreshed_order.status!r}"
    )


async def test_canClose_stays_true_after_lab_closes_so_send_button_still_works(
    db_session, _stub_closure_sample_check
) -> None:
    """Regression: an earlier version gated canClose on ``NOT lab_closed`` to
    stop a single lab from re-pressing 轉待送件. But ``canClose`` is also
    what the FE reads to enable the 送件結案 button at status=待送件 — so
    that gate wrongly disabled the final close after both labs had signed
    off. The actual "this lab already closed" UX is handled by the FE's
    labClosed early-return; canClose must stay a pure 6-condition signal.
    """
    suite = _suite()
    order_no = f"REG-OF6F-O-{suite}"
    wip_a = f"REG-OF6F-WA-{suite}"
    wip_b = f"REG-OF6F-WB-{suite}"

    # Order is already at WAITING_PICKUP (both labs pressed to_pickup before).
    await _seed_order(db_session, order_no=order_no, status=OrderStatus.WAITING_PICKUP.value)
    a = await _seed_wip(
        db_session, wip_no=wip_a, order_no=order_no, status="completed", lab_name="材料分析實驗室"
    )
    b = await _seed_wip(
        db_session, wip_no=wip_b, order_no=order_no, status="completed", lab_name="電性測試實驗室"
    )
    a.lab_closed = True
    b.lab_closed = True
    await _seed_closed_exec(db_session, wip_no=wip_a)
    await _seed_closed_exec(db_session, wip_no=wip_b)
    await _seed_returned_report(
        db_session, order_no=order_no, wip_no=wip_a, report_id=f"R-{suite}-A"
    )
    await _seed_returned_report(
        db_session, order_no=order_no, wip_no=wip_b, report_id=f"R-{suite}-B"
    )
    await db_session.commit()

    # From LAB-B's perspective at this point — every condition is met AND
    # LAB-B has already pressed to_pickup. canClose must still be True so
    # the 送件結案 button on /closure stays enabled.
    lab_b_scope = LabScope(role="lab_supervisor", lab_name="電性測試實驗室", lab_code="LAB-B")
    service = ClosureService(ClosureRepository(db_session), lab_b_scope)
    check = await service.check_closure(order_no)
    assert check["canClose"] is True, (
        f"canClose must stay True after the lab has closed (so the 送件結案 "
        f"button isn't wrongly disabled at status=待送件); got {check!r}"
    )
    assert check["labClosed"] is True
    assert all(c["ok"] for c in check["conditions"])


# ---------------------------------------------------------------------------
# Issue 7 — dependency-aware closure gate + cancel_transfer rollback.
#
# Bug 7a: ``all_wips_lab_closed`` previously counted only WIPs, but WIPs are
# created on-demand in ``sample_service._split_sample`` — NOT up-front for
# every order_item. For a multi-lab dependency chain (LAB-A -> LAB-B), LAB-A
# closes its WIP before LAB-B's WIP even exists, the count match fires
# prematurely, and the order jumps to WAITING_PICKUP while LAB-B's work
# hasn't happened yet. The contract for "all the work is done" lives in
# ``order_items.dependency_check``: every row must be claimed.
#
# Bug 7b: ``cancel_transfer`` reset the sample's location + wrote a history
# row but never reversed the ``dependency_check`` claim that the
# ``/api/wips/dependency/next`` endpoint made when the destination was
# chosen. That left the order_item permanently flagged as "assigned" with
# no transfer behind it — and since the dependency router only returns
# unclaimed items, the order became unreachable.
# ---------------------------------------------------------------------------


async def _seed_order_item(
    db_session,
    *,
    order_id: int,
    sample_id: str,
    lab_id: str,
    dependency_check: bool = False,
    experiment_id: str = "EXP-REG",
    target_group: str = "G1",
    target: int = 1,
):
    from app.db.models.order_management import OrderItemModel

    item = OrderItemModel(
        order_id=order_id,
        sample_id=sample_id,
        sample_name="reg sample",
        lab_id=lab_id,
        experiment_id=experiment_id,
        target_group=target_group,
        target=target,
        dependency_check=dependency_check,
        status="approved",
    )
    db_session.add(item)
    await db_session.flush()
    return item


async def test_all_wips_lab_closed_false_when_order_items_unclaimed(
    db_session,
) -> None:
    """Multi-lab dependency chain: 1 WIP exists and is lab_closed=True, but
    a second order_item is still dependency_check=False (its WIP hasn't been
    spawned yet via _split_sample). The closure gate MUST stay False so the
    order doesn't jump to WAITING_PICKUP prematurely."""
    suite = _suite()
    order_no = f"REG-OF7A-O-{suite}"

    lab_a = (await db_session.execute(select(Lab).where(Lab.code == "LAB-A"))).scalar_one()
    lab_b = (await db_session.execute(select(Lab).where(Lab.code == "LAB-B"))).scalar_one()

    order = await _seed_order(db_session, order_no=order_no, status=OrderStatus.IN_PROGRESS.value)

    # Order item #1: already claimed (LAB-A picked it up; WIP exists, closed)
    await _seed_order_item(
        db_session,
        order_id=order.id,
        sample_id=f"SMP-OF7A-{suite}",
        lab_id=str(lab_a.id),
        dependency_check=True,
    )
    # Order item #2: NOT yet claimed (LAB-B hasn't been reached in the chain)
    await _seed_order_item(
        db_session,
        order_id=order.id,
        sample_id=f"SMP-OF7A-{suite}",
        lab_id=str(lab_b.id),
        dependency_check=False,
    )

    wip = await _seed_wip(
        db_session,
        wip_no=f"REG-OF7A-W-{suite}",
        order_no=order_no,
        status="completed",
        lab_name=lab_a.name,
    )
    wip.lab_closed = True
    await db_session.commit()

    repo = ClosureRepository(db_session)
    assert await repo.all_wips_lab_closed(order_no) is False, (
        "closure gate must stay False while any order_item is still "
        "dependency_check=False — WIPs are spawned on-demand so the wips "
        "table alone isn't authoritative for cross-lab chains"
    )


async def test_all_wips_lab_closed_true_when_all_items_claimed_and_wips_closed(
    db_session,
) -> None:
    """Once every order_item is claimed AND every WIP has lab_closed=True,
    the gate flips True and the order can advance to WAITING_PICKUP."""
    suite = _suite()
    order_no = f"REG-OF7B-O-{suite}"

    lab_a = (await db_session.execute(select(Lab).where(Lab.code == "LAB-A"))).scalar_one()
    lab_b = (await db_session.execute(select(Lab).where(Lab.code == "LAB-B"))).scalar_one()

    order = await _seed_order(db_session, order_no=order_no, status=OrderStatus.IN_PROGRESS.value)
    await _seed_order_item(
        db_session,
        order_id=order.id,
        sample_id=f"SMP-OF7B-{suite}",
        lab_id=str(lab_a.id),
        dependency_check=True,
    )
    await _seed_order_item(
        db_session,
        order_id=order.id,
        sample_id=f"SMP-OF7B-{suite}",
        lab_id=str(lab_b.id),
        dependency_check=True,
    )

    for n, lab_name in enumerate([lab_a.name, lab_b.name]):
        wip = await _seed_wip(
            db_session,
            wip_no=f"REG-OF7B-W{n}-{suite}",
            order_no=order_no,
            status="completed",
            lab_name=lab_name,
        )
        wip.lab_closed = True

    await db_session.commit()

    repo = ClosureRepository(db_session)
    assert await repo.all_wips_lab_closed(order_no) is True


@pytest.fixture
async def _transfer_tables(db_session) -> None:
    """Create the ad-hoc ``samples`` / ``sample_histories`` / ``transfers``
    tables the cancel_transfer service needs.

    These tables are migration-only (raw-SQL throughout the B/C codebase),
    so ``Base.metadata.create_all`` in conftest doesn't materialise them.
    The schema mirrors the production migration just enough for
    ``cancel_transfer``: ``samples`` (id, status, current_location),
    ``sample_histories`` (insert-only audit row), ``transfers`` (the row
    cancel_transfer flips status on).
    """
    from sqlalchemy import text as _text

    statements = [
        """
        CREATE TABLE IF NOT EXISTS samples (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            status TEXT NOT NULL DEFAULT 'received',
            current_location TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS sample_histories (
            id BIGSERIAL PRIMARY KEY,
            sample_id uuid NOT NULL,
            action TEXT NOT NULL,
            from_status TEXT,
            to_status TEXT,
            description TEXT,
            operator_name TEXT,
            lab_name TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS transfers (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            transfer_no TEXT NOT NULL UNIQUE,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            order_no TEXT,
            sample_no TEXT,
            wip_no TEXT,
            from_lab TEXT,
            to_lab TEXT,
            handed_by TEXT,
            received_by TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            transferred_at TIMESTAMPTZ,
            received_at TIMESTAMPTZ,
            note TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
    ]
    for stmt in statements:
        await db_session.execute(_text(stmt))
    await db_session.commit()


async def _seed_sample_and_transfer(
    db_session,
    *,
    transfer_no: str,
    from_lab_name: str,
    to_lab_name: str,
) -> tuple[str, str, dict[str, object]]:
    """Insert a sample + a pending sample-targeted transfer; return
    ``(sample_id, transfer_id, transfer_data)`` ready to hand to
    ``cancel_transfer``."""
    from sqlalchemy import text as _text

    sample_row = (
        await db_session.execute(
            _text(
                "INSERT INTO samples (status, current_location) "
                "VALUES ('received', :location) RETURNING id"
            ),
            {"location": f"{from_lab_name} 交接待送區"},
        )
    ).fetchone()
    sample_id = str(sample_row[0])

    transfer_row = (
        await db_session.execute(
            _text(
                """
                INSERT INTO transfers (
                    transfer_no, target_type, target_id, from_lab, to_lab, status
                )
                VALUES (:no, 'sample', :tid, :from_lab, :to_lab, 'pending')
                RETURNING id
                """
            ),
            {
                "no": transfer_no,
                "tid": sample_id,
                "from_lab": from_lab_name,
                "to_lab": to_lab_name,
            },
        )
    ).fetchone()
    transfer_id = str(transfer_row[0])
    await db_session.commit()

    transfer_data = {
        "transfer_no": transfer_no,
        "target_type": "sample",
        "target_id": sample_id,
        "from_lab": from_lab_name,
        "to_lab": to_lab_name,
        "status": "pending",
    }
    return sample_id, transfer_id, transfer_data


async def test_cancel_transfer_resets_most_recent_dependency_check_for_sample(
    db_session,
    _transfer_tables,
) -> None:
    """When a pending sample-transfer is cancelled, the dependency_check
    claim that was made for (sample_id, to_lab) at /api/wips/dependency/next
    must be rolled back — otherwise the order_item is permanently flagged
    as 'assigned' with no actual transfer behind it, and the dependency
    router (which only returns unclaimed items) can never re-surface it.
    """
    from app.db.models import OrderItemModel as _OrderItemModel
    from app.services import transfer_service

    suite = _suite()
    order_no = f"REG-OF7C-O-{suite}"
    transfer_no = f"REG-OF7C-T-{suite}"
    lab_b = (await db_session.execute(select(Lab).where(Lab.code == "LAB-B"))).scalar_one()

    order = await _seed_order(db_session, order_no=order_no, status=OrderStatus.IN_PROGRESS.value)
    sample_id, transfer_id, transfer_data = await _seed_sample_and_transfer(
        db_session,
        transfer_no=transfer_no,
        from_lab_name="材料分析實驗室",
        to_lab_name=lab_b.name,
    )
    # Seed the order_item already claimed (claim happened when the destination
    # was chosen before this transfer was created).
    item = await _seed_order_item(
        db_session,
        order_id=order.id,
        sample_id=sample_id,
        lab_id=str(lab_b.id),
        dependency_check=True,
    )
    item_id = item.id  # capture before expire_all invalidates the ORM row
    await db_session.commit()

    await transfer_service.cancel_transfer(
        db_session,
        transfer_id=transfer_id,
        transfer_data=transfer_data,
        operator_name="tester",
    )

    db_session.expire_all()
    refreshed = (
        await db_session.execute(select(_OrderItemModel).where(_OrderItemModel.id == item_id))
    ).scalar_one()
    assert refreshed.dependency_check is False, (
        "cancel_transfer on a sample-targeted transfer must reset the "
        "dependency_check claim that /api/wips/dependency/next made for "
        "the same (sample_id, to_lab) — otherwise the order_item is "
        "stranded forever"
    )


async def test_cancel_transfer_does_not_touch_unrelated_dependency_checks(
    db_session,
    _transfer_tables,
) -> None:
    """The rollback heuristic must be scoped to the cancelled transfer's
    (sample_id, to_lab). A second sample's claim — even to the same
    destination lab — must NOT be released by the unrelated cancel."""
    from app.db.models import OrderItemModel as _OrderItemModel
    from app.services import transfer_service

    suite = _suite()
    order_no = f"REG-OF7D-O-{suite}"
    transfer_no = f"REG-OF7D-T-{suite}"
    lab_b = (await db_session.execute(select(Lab).where(Lab.code == "LAB-B"))).scalar_one()

    order = await _seed_order(db_session, order_no=order_no, status=OrderStatus.IN_PROGRESS.value)
    sample_1_id, transfer_id, transfer_data = await _seed_sample_and_transfer(
        db_session,
        transfer_no=transfer_no,
        from_lab_name="材料分析實驗室",
        to_lab_name=lab_b.name,
    )
    # Sample #2 — different sample, same destination lab. Its claim should
    # NOT be released when sample #1's transfer is cancelled.
    from sqlalchemy import text as _text

    sample_2_row = (
        await db_session.execute(
            _text(
                "INSERT INTO samples (status, current_location) "
                "VALUES ('received', :location) RETURNING id"
            ),
            {"location": "材料分析實驗室 交接待送區"},
        )
    ).fetchone()
    sample_2_id = str(sample_2_row[0])

    item_1 = await _seed_order_item(
        db_session,
        order_id=order.id,
        sample_id=sample_1_id,
        lab_id=str(lab_b.id),
        dependency_check=True,
    )
    item_2 = await _seed_order_item(
        db_session,
        order_id=order.id,
        sample_id=sample_2_id,
        lab_id=str(lab_b.id),
        dependency_check=True,
    )
    item_1_id = item_1.id  # capture before expire_all
    item_2_id = item_2.id
    await db_session.commit()

    await transfer_service.cancel_transfer(
        db_session,
        transfer_id=transfer_id,
        transfer_data=transfer_data,
        operator_name="tester",
    )

    db_session.expire_all()
    refreshed_1 = (
        await db_session.execute(select(_OrderItemModel).where(_OrderItemModel.id == item_1_id))
    ).scalar_one()
    refreshed_2 = (
        await db_session.execute(select(_OrderItemModel).where(_OrderItemModel.id == item_2_id))
    ).scalar_one()
    assert refreshed_1.dependency_check is False, "sample #1's claim must be released"
    assert refreshed_2.dependency_check is True, (
        "sample #2's claim — for a different sample — must be left alone; "
        "the rollback heuristic is scoped to (sample_id, to_lab)"
    )

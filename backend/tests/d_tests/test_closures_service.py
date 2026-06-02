"""Unit/behaviour tests for the closures module (組員 D).

These exercise ``ClosureService`` + ``ClosureRepository`` directly against the
test database (matching the style in ``tests/test_order_flow_regressions.py``),
filling the branch gaps left by the regression suite:

* ``_enforce_order_access`` — cross-lab ForbiddenError + restricted-without-lab.
* ``list_closures`` / ``list_storage`` — restricted-without-lab early return.
* ``storage_inbound`` / ``storage_outbound`` — happy path + status guards +
  "no storage rows" NotFoundError.
* ``close_order`` — happy path + wrong-status guard + "still has samples" guard.
* ``_send_pickup_reminder`` — broker-down synchronous fallback path.
* Repository: ``list_storage`` (status + lab filter), ``storage_items``,
  ``count_reports_in_status``, ``find_user_email_by_applicant``.

``samples`` is B's raw-SQL table and is not in ``Base.metadata`` (the test DB is
built from ``create_all``), so any path that reads ``ClosureRepository.sample_statuses``
is stubbed via monkeypatch — same approach as the regression suite.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.common.dependencies.lab_scope import LabScope
from app.common.enums import OrderStatus, StorageStatus
from app.common.enums.role_d_zh import STORAGE_ZH
from app.common.errors import ConflictError, ForbiddenError, NotFoundError
from app.db.models import OrderModel, Storage, Wip
from app.modules.closures.repository import ClosureRepository
from app.modules.closures.service import ClosureService

pytestmark = pytest.mark.asyncio

LAB_A_NAME = "材料分析實驗室"
LAB_B_NAME = "電性測試實驗室"


def _suite() -> str:
    return uuid.uuid4().hex[:8]


def _lab_a_scope() -> LabScope:
    return LabScope(role="lab_supervisor", lab_name=LAB_A_NAME, lab_code="LAB-A")


def _restricted_scope() -> LabScope:
    """A non-admin user with no lab — sees nothing."""
    return LabScope(role="lab_engineer", lab_name=None, lab_code=None)


async def _seed_order(db_session, *, order_no: str, status: str, applicant_id: str) -> OrderModel:
    order = OrderModel(
        order_no=order_no,
        applicant_id=applicant_id,
        department_id="DEPT-RD",
        apply_date=datetime.now(UTC),
        status=status,
        priority="normal",
        total_items=1,
    )
    db_session.add(order)
    await db_session.flush()
    return order


async def _seed_wip(db_session, *, wip_no: str, order_no: str, lab_name: str) -> Wip:
    wip = Wip(
        wip_no=wip_no,
        sample_id=uuid.uuid4(),
        order_no=order_no,
        lab_name=lab_name,
        experiment_item="closure-test",
        priority="normal",
        status="completed",
        progress=100,
    )
    db_session.add(wip)
    await db_session.flush()
    return wip


async def _seed_storage(db_session, *, order_no: str, storage_id: str, status: str) -> Storage:
    s = Storage(
        storage_id=storage_id,
        order_id=order_no,
        sample="S-1",
        qty="3",
        status=status,
        location="A-01",
    )
    db_session.add(s)
    await db_session.flush()
    return s


# ---------------------------------------------------------------------------
# _enforce_order_access
# ---------------------------------------------------------------------------


async def test_enforce_order_access_blocks_other_lab(db_session) -> None:
    """A lab-scoped user can't touch an order whose WIPs all belong to another lab."""
    suite = _suite()
    order_no = f"CLS-ACC-{suite}"
    await _seed_order(
        db_session, order_no=order_no, status=OrderStatus.IN_PROGRESS.value, applicant_id="x"
    )
    await _seed_wip(db_session, wip_no=f"W-{suite}", order_no=order_no, lab_name=LAB_B_NAME)
    await db_session.commit()

    service = ClosureService(ClosureRepository(db_session), _lab_a_scope())
    with pytest.raises(ForbiddenError):
        await service.check_closure(order_no)


async def test_enforce_order_access_restricted_without_lab_forbidden(db_session) -> None:
    """A non-admin with no lab is rejected before any DB lookup."""
    suite = _suite()
    order_no = f"CLS-NOLAB-{suite}"
    await _seed_order(
        db_session, order_no=order_no, status=OrderStatus.IN_PROGRESS.value, applicant_id="x"
    )
    await db_session.commit()

    service = ClosureService(ClosureRepository(db_session), _restricted_scope())
    with pytest.raises(ForbiddenError):
        await service.check_closure(order_no)


async def test_check_closure_missing_order_is_not_found(db_session) -> None:
    """A system_admin (passes access) hitting a non-existent order gets NotFoundError."""
    service = ClosureService(ClosureRepository(db_session), LabScope.system())
    with pytest.raises(NotFoundError):
        await service.check_closure(f"CLS-NOPE-{_suite()}")


# ---------------------------------------------------------------------------
# list_closures / list_storage — restricted-without-lab short-circuit
# ---------------------------------------------------------------------------


async def test_list_closures_restricted_without_lab_returns_empty(db_session) -> None:
    service = ClosureService(ClosureRepository(db_session), _restricted_scope())
    assert await service.list_closures() == []


async def test_list_storage_restricted_without_lab_returns_empty(db_session) -> None:
    service = ClosureService(ClosureRepository(db_session), _restricted_scope())
    assert await service.list_storage() == []


async def test_list_storage_returns_serialized_items_for_admin(db_session) -> None:
    suite = _suite()
    order_no = f"CLS-LS-{suite}"
    storage_id = f"ST-{suite}"
    await _seed_order(
        db_session, order_no=order_no, status=OrderStatus.WAITING_PICKUP.value, applicant_id="x"
    )
    await _seed_storage(
        db_session,
        order_no=order_no,
        storage_id=storage_id,
        status=STORAGE_ZH[StorageStatus.IN_LAB],
    )
    await db_session.commit()

    service = ClosureService(ClosureRepository(db_session), LabScope.system())
    items = await service.list_storage()
    mine = [i for i in items if i["storageId"] == storage_id]
    assert len(mine) == 1
    assert mine[0]["orderId"] == order_no
    assert mine[0]["history"] == []


# ---------------------------------------------------------------------------
# storage_inbound
# ---------------------------------------------------------------------------


async def test_storage_inbound_no_records_is_not_found(db_session) -> None:
    suite = _suite()
    order_no = f"CLS-IN-EMPTY-{suite}"
    await _seed_order(
        db_session, order_no=order_no, status=OrderStatus.IN_PROGRESS.value, applicant_id="x"
    )
    await db_session.commit()

    service = ClosureService(ClosureRepository(db_session), LabScope.system())
    with pytest.raises(NotFoundError):
        await service.storage_inbound(order_no, operator="op", note="n")


async def test_storage_inbound_moves_in_lab_to_stored_and_records_history(db_session) -> None:
    suite = _suite()
    order_no = f"CLS-IN-{suite}"
    storage_id = f"ST-IN-{suite}"
    await _seed_order(
        db_session, order_no=order_no, status=OrderStatus.IN_PROGRESS.value, applicant_id="x"
    )
    await _seed_storage(
        db_session,
        order_no=order_no,
        storage_id=storage_id,
        status=STORAGE_ZH[StorageStatus.IN_LAB],
    )
    await db_session.commit()

    service = ClosureService(ClosureRepository(db_session), LabScope.system())
    result = await service.storage_inbound(order_no, operator="王工", note="收到")

    assert result["orderId"] == order_no
    item = next(i for i in result["items"] if i["storageId"] == storage_id)
    assert item["status"] == STORAGE_ZH[StorageStatus.STORED]
    assert item["history"][-1]["action"] == "入庫"
    assert item["history"][-1]["by"] == "王工"


async def test_storage_inbound_leaves_already_stored_untouched(db_session) -> None:
    """Only IN_LAB rows are advanced; an already-STORED row gets no new history."""
    suite = _suite()
    order_no = f"CLS-IN-NOOP-{suite}"
    storage_id = f"ST-NOOP-{suite}"
    await _seed_order(
        db_session, order_no=order_no, status=OrderStatus.IN_PROGRESS.value, applicant_id="x"
    )
    await _seed_storage(
        db_session,
        order_no=order_no,
        storage_id=storage_id,
        status=STORAGE_ZH[StorageStatus.STORED],
    )
    await db_session.commit()

    service = ClosureService(ClosureRepository(db_session), LabScope.system())
    result = await service.storage_inbound(order_no, operator=None, note=None)
    item = next(i for i in result["items"] if i["storageId"] == storage_id)
    assert item["status"] == STORAGE_ZH[StorageStatus.STORED]
    assert item["history"] == []


# ---------------------------------------------------------------------------
# storage_outbound
# ---------------------------------------------------------------------------


async def test_storage_outbound_wrong_status_conflicts(db_session) -> None:
    """Outbound only allowed at WAITING_PICKUP."""
    suite = _suite()
    order_no = f"CLS-OUT-BAD-{suite}"
    await _seed_order(
        db_session, order_no=order_no, status=OrderStatus.IN_PROGRESS.value, applicant_id="x"
    )
    await db_session.commit()

    service = ClosureService(ClosureRepository(db_session), LabScope.system())
    with pytest.raises(ConflictError):
        await service.storage_outbound(order_no, operator=None, note=None)


async def test_storage_outbound_no_records_is_not_found(db_session) -> None:
    suite = _suite()
    order_no = f"CLS-OUT-EMPTY-{suite}"
    await _seed_order(
        db_session, order_no=order_no, status=OrderStatus.WAITING_PICKUP.value, applicant_id="x"
    )
    await db_session.commit()

    service = ClosureService(ClosureRepository(db_session), LabScope.system())
    with pytest.raises(NotFoundError):
        await service.storage_outbound(order_no, operator=None, note=None)


async def test_storage_outbound_marks_picked_up_and_records_history(db_session) -> None:
    suite = _suite()
    order_no = f"CLS-OUT-{suite}"
    storage_id = f"ST-OUT-{suite}"
    await _seed_order(
        db_session, order_no=order_no, status=OrderStatus.WAITING_PICKUP.value, applicant_id="x"
    )
    await _seed_storage(
        db_session,
        order_no=order_no,
        storage_id=storage_id,
        status=STORAGE_ZH[StorageStatus.STORED],
    )
    await db_session.commit()

    service = ClosureService(ClosureRepository(db_session), LabScope.system())
    result = await service.storage_outbound(order_no, operator="李工", note="取走")
    item = next(i for i in result["items"] if i["storageId"] == storage_id)
    assert item["status"] == STORAGE_ZH[StorageStatus.PICKED_UP]
    assert item["history"][-1]["action"] == "出庫取件"
    assert item["history"][-1]["by"] == "李工"


# ---------------------------------------------------------------------------
# close_order
# ---------------------------------------------------------------------------


async def test_close_order_wrong_status_conflicts(db_session) -> None:
    suite = _suite()
    order_no = f"CLS-CLOSE-BAD-{suite}"
    await _seed_order(
        db_session, order_no=order_no, status=OrderStatus.IN_PROGRESS.value, applicant_id="x"
    )
    await db_session.commit()

    service = ClosureService(ClosureRepository(db_session), LabScope.system())
    with pytest.raises(ConflictError):
        await service.close_order(order_no, operator=None)


async def test_close_order_blocks_when_samples_not_picked_up(db_session, monkeypatch) -> None:
    """At WAITING_PICKUP but samples not all picked_up → ConflictError."""
    suite = _suite()
    order_no = f"CLS-CLOSE-SAMPLE-{suite}"
    await _seed_order(
        db_session, order_no=order_no, status=OrderStatus.WAITING_PICKUP.value, applicant_id="x"
    )
    await db_session.commit()

    async def _not_picked(_self, _order_no):
        return ["in_storage"]

    monkeypatch.setattr(ClosureRepository, "sample_statuses", _not_picked)
    service = ClosureService(ClosureRepository(db_session), LabScope.system())
    with pytest.raises(ConflictError):
        await service.close_order(order_no, operator=None)


async def test_close_order_succeeds_when_all_samples_picked_up(db_session, monkeypatch) -> None:
    suite = _suite()
    order_no = f"CLS-CLOSE-OK-{suite}"
    await _seed_order(
        db_session, order_no=order_no, status=OrderStatus.WAITING_PICKUP.value, applicant_id="x"
    )
    await db_session.commit()

    async def _picked(_self, _order_no):
        return ["picked_up", "picked_up"]

    monkeypatch.setattr(ClosureRepository, "sample_statuses", _picked)
    service = ClosureService(ClosureRepository(db_session), LabScope.system())
    result = await service.close_order(order_no, operator="主管")

    db_session.expire_all()
    refreshed = (
        await db_session.execute(select(OrderModel).where(OrderModel.order_no == order_no))
    ).scalar_one()
    assert refreshed.status == OrderStatus.CLOSED.value
    assert result["status"] == "已結案"


# ---------------------------------------------------------------------------
# _send_pickup_reminder — broker-down synchronous fallback
# ---------------------------------------------------------------------------


async def test_send_pickup_reminder_falls_back_to_sync_when_broker_down(
    db_session, monkeypatch
) -> None:
    """If ``.delay`` raises (broker unreachable), the reminder is sent
    synchronously via ``.run`` instead, and the failure does not bubble up."""
    import app.workers.email_sender as email_sender

    suite = _suite()
    order = OrderModel(
        order_no=f"CLS-REM-{suite}",
        applicant_id="not-a-uuid",  # forces the placeholder-recipient branch
        department_id="DEPT-RD",
        apply_date=datetime.now(UTC),
        status=OrderStatus.WAITING_PICKUP.value,
        priority="normal",
        total_items=1,
    )

    ran: dict = {}

    def _boom_delay(*_a, **_kw):
        raise RuntimeError("broker down")

    def _capture_run(*, to, order_id, applicant=None):
        ran.update(to=to, order_id=order_id, applicant=applicant)
        return {"status": "queued", "to": to}

    monkeypatch.setattr(email_sender.send_pickup_reminder_email, "delay", _boom_delay)
    monkeypatch.setattr(email_sender.send_pickup_reminder_email, "run", _capture_run)

    service = ClosureService(ClosureRepository(db_session), LabScope.system())
    # Must not raise even though the broker is "down".
    await service._send_pickup_reminder(order)

    assert ran["order_id"] == order.order_no
    # applicant_id is not a UUID → no email resolved → placeholder is applicant_id.
    assert ran["to"] == "not-a-uuid"


# ---------------------------------------------------------------------------
# ClosureRepository direct coverage
# ---------------------------------------------------------------------------


async def test_repo_list_storage_filters_by_status(db_session) -> None:
    suite = _suite()
    order_no = f"CLS-RLS-{suite}"
    await _seed_order(
        db_session, order_no=order_no, status=OrderStatus.WAITING_PICKUP.value, applicant_id="x"
    )
    stored_id = f"ST-S-{suite}"
    picked_id = f"ST-P-{suite}"
    await _seed_storage(
        db_session, order_no=order_no, storage_id=stored_id, status=STORAGE_ZH[StorageStatus.STORED]
    )
    await _seed_storage(
        db_session,
        order_no=order_no,
        storage_id=picked_id,
        status=STORAGE_ZH[StorageStatus.PICKED_UP],
    )
    await db_session.commit()

    repo = ClosureRepository(db_session)
    stored = await repo.list_storage(status=STORAGE_ZH[StorageStatus.STORED])
    ids = {s.storage_id for s in stored}
    assert stored_id in ids
    assert picked_id not in ids


async def test_repo_list_storage_filters_by_lab(db_session) -> None:
    """Storage rows are joined to WIPs to resolve their lab; a LAB-B filter
    excludes a LAB-A-only order's storage."""
    suite = _suite()
    order_no = f"CLS-RLAB-{suite}"
    storage_id = f"ST-LAB-{suite}"
    await _seed_order(
        db_session, order_no=order_no, status=OrderStatus.WAITING_PICKUP.value, applicant_id="x"
    )
    await _seed_wip(db_session, wip_no=f"W-{suite}", order_no=order_no, lab_name=LAB_A_NAME)
    await _seed_storage(
        db_session,
        order_no=order_no,
        storage_id=storage_id,
        status=STORAGE_ZH[StorageStatus.STORED],
    )
    await db_session.commit()

    repo = ClosureRepository(db_session)
    lab_a = {s.storage_id for s in await repo.list_storage(lab_name=LAB_A_NAME)}
    lab_b = {s.storage_id for s in await repo.list_storage(lab_name=LAB_B_NAME)}
    assert storage_id in lab_a
    assert storage_id not in lab_b


async def test_repo_count_reports_in_status(db_session) -> None:
    """``count_reports_in_status`` counts only rows in the requested statuses."""
    from app.common.enums import ReportStatus
    from app.common.enums.role_d_zh import REPORT_ZH
    from app.db.models.reports import Report

    suite = _suite()
    order_no = f"CLS-RPT-{suite}"
    await _seed_order(
        db_session, order_no=order_no, status=OrderStatus.IN_PROGRESS.value, applicant_id="x"
    )
    db_session.add(
        Report(
            report_id=f"R-{suite}",
            order_id=order_no,
            wip_id=f"W-{suite}",
            title="t",
            summary="",
            conclusion="",
            status=REPORT_ZH[ReportStatus.RETURNED],
            created_by="tester",
        )
    )
    await db_session.commit()

    repo = ClosureRepository(db_session)
    returned = REPORT_ZH[ReportStatus.RETURNED]
    assert await repo.count_reports_in_status(order_no, [returned]) == 1
    # A status no report is in → 0.
    assert await repo.count_reports_in_status(order_no, ["不存在的狀態"]) == 0


async def test_repo_find_user_email_non_uuid_returns_none(db_session) -> None:
    repo = ClosureRepository(db_session)
    assert await repo.find_user_email_by_applicant("definitely-not-a-uuid") is None
    assert await repo.find_user_email_by_applicant(None) is None  # type: ignore[arg-type]


async def test_repo_find_user_email_unknown_uuid_returns_none(db_session) -> None:
    repo = ClosureRepository(db_session)
    # Valid UUID shape but no matching user.
    assert await repo.find_user_email_by_applicant(str(uuid.uuid4())) is None


async def test_repo_find_user_email_resolves_seeded_user(db_session) -> None:
    """A real seeded user's UUID resolves to their email."""
    from app.db.models.users import User

    admin = (
        await db_session.execute(select(User).where(User.email == "admin@example.com"))
    ).scalar_one()
    repo = ClosureRepository(db_session)
    assert await repo.find_user_email_by_applicant(str(admin.id)) == "admin@example.com"

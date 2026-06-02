from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.common.dependencies.lab_scope import LabScope
from app.common.enums import OrderStatus, WipStatus
from app.common.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.db.models import Wip, WipExecution
from app.modules.experiment_runs.service import ABORT_PENDING, B_DISPATCHED, ExperimentRunService

pytestmark = pytest.mark.asyncio


LAB_SCOPE = LabScope(role="lab_engineer", lab_name="材料分析實驗室", lab_code="LAB-A")
NO_LAB_SCOPE = LabScope(role="lab_engineer", lab_name=None, lab_code=None)


class FakeExperimentRepo:
    def __init__(self) -> None:
        self.wips: dict[str, Wip] = {}
        self.execs: dict[str, WipExecution] = {}
        self.orders: dict[str, SimpleNamespace] = {}
        self.dispatches: dict[str, tuple[str | None, str | None]] = {}
        self.operators = [("Alice", "lab_engineer"), ("Alice", "lab_supervisor")]
        self.commits = 0
        self.session = SimpleNamespace()

    async def get_wip(self, wip_no: str) -> Wip | None:
        return self.wips.get(wip_no)

    async def list_wips(self, lab_name: str | None = None) -> list[Wip]:
        return [w for w in self.wips.values() if lab_name is None or w.lab_name == lab_name]

    async def get_exec(self, wip_no: str) -> WipExecution | None:
        return self.execs.get(wip_no)

    async def get_execs_map(self, wip_nos: list[str]) -> dict[str, WipExecution]:
        return {wip_no: self.execs[wip_no] for wip_no in wip_nos if wip_no in self.execs}

    async def ensure_exec(self, wip_no: str) -> WipExecution:
        if wip_no not in self.execs:
            self.execs[wip_no] = execution(wip_no)
        return self.execs[wip_no]

    async def get_dispatch_assignment(self, wip_no: str) -> tuple[str | None, str | None]:
        return self.dispatches.get(wip_no, (None, None))

    async def get_dispatch_assignments(
        self, wip_nos: list[str]
    ) -> dict[str, tuple[str | None, str | None]]:
        return {wip_no: self.dispatches.get(wip_no, (None, None)) for wip_no in wip_nos}

    async def list_lab_operators(self, _lab_name: str) -> list[tuple[str, str]]:
        return self.operators

    async def get_order(self, order_no: str) -> SimpleNamespace | None:
        return self.orders.get(order_no)

    async def list_wips_for_order(self, order_no: str) -> list[Wip]:
        return [w for w in self.wips.values() if w.order_no == order_no]

    async def commit(self) -> None:
        self.commits += 1


def wip(
    wip_no: str = "WIP-1",
    *,
    status: str = B_DISPATCHED,
    lab_name: str = "材料分析實驗室",
) -> Wip:
    item = Wip(
        id=uuid.uuid4(),
        wip_no=wip_no,
        sample_id=uuid.uuid4(),
        order_no="ORD-1",
        lab_name=lab_name,
        experiment_item="SEM",
        priority="normal",
        status=status,
        progress=0,
    )
    item.history = []
    return item


def execution(wip_no: str = "WIP-1", status: str = WipStatus.WAITING_LOAD.value) -> WipExecution:
    return WipExecution(
        wip_no=wip_no,
        exec_status=status,
        machine_id=None,
        recipe=None,
        operator=None,
        data_verified=False,
    )


def service(repo: FakeExperimentRepo) -> ExperimentRunService:
    svc = ExperimentRunService(repo, LAB_SCOPE)

    async def noop(*_args: object, **_kwargs: object) -> None:
        return None

    svc._publish_wip_pipeline_change = noop  # type: ignore[method-assign]
    svc._advance_sample_flow = noop  # type: ignore[method-assign]
    svc._advance_sample_on_termination = noop  # type: ignore[method-assign]
    svc._notify_applicant_of_termination = noop  # type: ignore[method-assign]
    return svc


async def test_list_get_and_operator_helpers_respect_scope_and_fallbacks() -> None:
    repo = FakeExperimentRepo()
    repo.wips = {"WIP-1": wip(), "WIP-2": wip("WIP-2", lab_name="電性測試實驗室")}
    repo.execs["WIP-1"] = execution(status=WipStatus.RUNNING.value)
    repo.dispatches["WIP-1"] = ("SEM-A-001", "SEM-R1")

    rows = await service(repo).list_wips()
    assert [row["wipId"] for row in rows] == ["WIP-1"]
    assert await ExperimentRunService(repo, NO_LAB_SCOPE).list_wips() == []
    assert (await service(repo).get_wip("WIP-1"))["machineId"] == "SEM-A-001"
    assert await service(repo).list_operators("WIP-1") == [{"name": "Alice", "role": "實驗室主管"}]

    repo.wips["WIP-empty-lab"] = wip("WIP-empty-lab", lab_name=None)
    assert await ExperimentRunService(repo, LabScope.system()).list_operators("WIP-empty-lab") == []

    with pytest.raises(NotFoundError):
        await service(repo).get_wip("missing")
    with pytest.raises(ForbiddenError):
        await service(repo).get_wip("WIP-2")


async def test_check_in_out_progress_and_upload_result_lifecycle() -> None:
    repo = FakeExperimentRepo()
    repo.wips["WIP-1"] = wip()
    repo.execs["WIP-1"] = execution()
    repo.orders["ORD-1"] = SimpleNamespace(status=OrderStatus.SCHEDULED.value)
    svc = service(repo)

    checked_in = await svc.check_in("WIP-1", "Alice", "SEM-A-001", "SEM-R1")
    assert checked_in["status"] == "執行中"
    assert repo.orders["ORD-1"].status == OrderStatus.IN_PROGRESS.value
    check_in_history = repo.wips["WIP-1"].history
    assert check_in_history, "check_in should append a history row"
    assert check_in_history[-1].action == "上機"

    updated = await svc.update_progress("WIP-1", 40)
    assert updated["progress"] == 40

    checked_out = await svc.check_out("WIP-1", "Alice", "done")
    assert checked_out["status"] == "已下機"

    uploaded = await svc.upload_result("WIP-1", "ok", "raw.csv", True)
    assert uploaded["status"] == "待確認"
    assert uploaded["progress"] == 100
    assert uploaded["dataVerified"] is True


async def test_lifecycle_methods_reject_wrong_statuses() -> None:
    repo = FakeExperimentRepo()
    repo.wips["WIP-1"] = wip(status="created")
    repo.execs["WIP-1"] = execution(status=WipStatus.WAITING_LOAD.value)
    svc = service(repo)

    with pytest.raises(ConflictError):
        await svc.check_in("WIP-1", "Alice", "SEM-A-001", "SEM-R1")
    repo.wips["WIP-1"].status = B_DISPATCHED
    repo.execs["WIP-1"].exec_status = WipStatus.UNLOADED.value
    with pytest.raises(ConflictError):
        await svc.check_in("WIP-1", "Alice", "SEM-A-001", "SEM-R1")
    with pytest.raises(ConflictError):
        await svc.update_progress("WIP-1", 10)
    with pytest.raises(ConflictError):
        await svc.check_out("WIP-1", "Alice", None)
    repo.execs["WIP-1"].exec_status = WipStatus.COMPLETED.value
    with pytest.raises(ConflictError):
        await svc.upload_result("WIP-1", "ok", None, True)


async def test_verify_and_confirm_result_roll_up_order_status() -> None:
    repo = FakeExperimentRepo()
    repo.wips["WIP-1"] = wip()
    repo.execs["WIP-1"] = execution(status=WipStatus.WAITING_CONFIRM.value)
    repo.orders["ORD-1"] = SimpleNamespace(status=OrderStatus.IN_PROGRESS.value)
    svc = service(repo)

    verified = await svc.verify_data("WIP-1", "Lead")
    assert verified["dataVerified"] is True
    with pytest.raises(ConflictError):
        await svc.verify_data("WIP-1", "Lead")

    confirmed = await svc.confirm_result("WIP-1", "Lead")
    assert confirmed["status"] == "已完成"
    assert repo.orders["ORD-1"].status == OrderStatus.COMPLETED.value

    repo.execs["WIP-1"].exec_status = WipStatus.WAITING_CONFIRM.value
    repo.execs["WIP-1"].data_verified = False
    with pytest.raises(ValidationError):
        await svc.confirm_result("WIP-1", "Lead")


async def test_abort_request_review_and_machine_completion() -> None:
    repo = FakeExperimentRepo()
    repo.wips["WIP-1"] = wip()
    repo.execs["WIP-1"] = execution(status=WipStatus.RUNNING.value)
    repo.orders["ORD-1"] = SimpleNamespace(status=OrderStatus.IN_PROGRESS.value)
    svc = service(repo)

    requested = await svc.request_abort("WIP-1", "broken", "Alice")
    assert requested["abort"]["status"] == ABORT_PENDING

    with pytest.raises(ConflictError):
        await svc.request_abort("WIP-1", "again", "Alice")

    rejected = await svc.review_abort("WIP-1", False, "continue", "Lead")
    assert rejected["abort"]["status"] == "已駁回"
    assert rejected["status"] == "執行中"

    repo.execs["WIP-1"].abort_status = ABORT_PENDING
    approved = await svc.review_abort("WIP-1", True, "stop", "Lead")
    assert approved["status"] == "已終止"
    assert repo.orders["ORD-1"].status == OrderStatus.TERMINATED.value

    repo.execs["WIP-1"].exec_status = WipStatus.RUNNING.value
    repo.execs["WIP-1"].machine_id = "SEM-A-001"
    assert await svc.apply_machine_completion("WIP-1") is True
    assert repo.execs["WIP-1"].exec_status == WipStatus.WAITING_CONFIRM.value
    assert repo.wips["WIP-1"].progress == 100

    repo.execs["WIP-1"].exec_status = WipStatus.COMPLETED.value
    assert await svc.apply_machine_completion("WIP-1") is False


async def test_abort_review_rejects_without_pending_request() -> None:
    repo = FakeExperimentRepo()
    repo.wips["WIP-1"] = wip()
    repo.execs["WIP-1"] = execution(status=WipStatus.RUNNING.value)

    with pytest.raises(ConflictError):
        await service(repo).review_abort("WIP-1", True, None, "Lead")

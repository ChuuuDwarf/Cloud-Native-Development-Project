from __future__ import annotations

import uuid

import pytest

from app.common.dependencies.lab_scope import LabScope
from app.common.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.db.models import Dispatch, Machine, Recipe, Wip
from app.modules.dispatches.schemas import AssignDispatchPayload, CreateDispatchPayload
from app.modules.dispatches.service import (
    STATUS_PENDING,
    STATUS_SCHEDULING,
    STATUS_WAITING_LOAD,
    DispatchService,
    _match_machine,
    _order_by_strategy,
)

pytestmark = pytest.mark.asyncio


LAB_SCOPE = LabScope(role="lab_engineer", lab_name="材料分析實驗室", lab_code="LAB-A")
NO_LAB_SCOPE = LabScope(role="lab_engineer", lab_name=None, lab_code=None)


class FakeDispatchRepo:
    def __init__(self) -> None:
        self.dispatches: dict[str, Dispatch] = {}
        self.wips: dict[str, Wip] = {}
        self.machines: dict[str, Machine] = {}
        self.recipes: dict[str, Recipe] = {}
        self.lab_codes = {"材料分析實驗室": "LAB-A", "電性測試實驗室": "LAB-B"}
        self.history: list[object] = []
        self.added: list[Dispatch] = []
        self.commits = 0

    async def list_dispatches(self, lab_code: str | None = None) -> list[Dispatch]:
        return [d for d in self.dispatches.values() if lab_code is None or d.lab == lab_code]

    async def list_by_statuses(self, statuses: list[str], lab_code: str | None = None):
        return [
            d
            for d in self.dispatches.values()
            if d.status in statuses and (lab_code is None or d.lab == lab_code)
        ]

    async def get_by_dispatch_id(self, dispatch_id: str) -> Dispatch | None:
        return self.dispatches.get(dispatch_id)

    async def get_wip_by_no(self, wip_no: str) -> Wip | None:
        return self.wips.get(wip_no)

    async def lab_code_for_name(self, lab_name: str) -> str | None:
        return self.lab_codes.get(lab_name)

    async def list_machines(self, lab_code: str | None = None) -> list[Machine]:
        return [m for m in self.machines.values() if lab_code is None or m.lab == lab_code]

    async def get_machine(self, machine_id: str) -> Machine | None:
        return self.machines.get(machine_id)

    async def get_recipe(self, recipe_id: str) -> Recipe | None:
        return self.recipes.get(recipe_id)

    def add(self, dispatch: Dispatch) -> None:
        self.added.append(dispatch)
        self.dispatches[dispatch.dispatch_id] = dispatch

    def add_wip_history(self, history: object) -> None:
        self.history.append(history)

    async def commit(self) -> None:
        self.commits += 1


def dispatch(
    dispatch_id: str,
    *,
    priority: str = "中",
    due_at: str | None = None,
    item: str = "SEM",
    status: str = STATUS_PENDING,
    lab: str = "LAB-A",
) -> Dispatch:
    return Dispatch(
        dispatch_id=dispatch_id,
        wip_id=f"WIP-{dispatch_id}",
        order_id="ORD-1",
        experiment_item=item,
        priority=priority,
        due_at=due_at,
        status=status,
        created_by="Alice",
        lab=lab,
    )


def machine(machine_id: str = "SEM-A-001", lab: str = "LAB-A", items: list[str] | None = None):
    return Machine(
        machine_id=machine_id,
        name=machine_id,
        lab=lab,
        status="閒置",
        supported_items=items or ["SEM"],
        utilization=0,
        owner="Alice",
    )


def recipe(recipe_id: str = "SEM-R1", item: str = "SEM", machine_ids: list[str] | None = None):
    return Recipe(
        recipe_id=recipe_id,
        name=recipe_id,
        version="v1",
        experiment_item=item,
        machine_ids=machine_ids or ["SEM-A-001"],
        method="method",
        parameters={},
        updated_by="Alice",
    )


def wip(wip_no: str = "WIP-1", lab_name: str = "材料分析實驗室", status: str = "created") -> Wip:
    return Wip(
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


def create_payload(dispatch_id: str = "D-1", wip_id: str = "WIP-1") -> CreateDispatchPayload:
    return CreateDispatchPayload.model_validate(
        {
            "dispatchId": dispatch_id,
            "wipId": wip_id,
            "orderId": "ORD-1",
            "experimentItem": "SEM",
            "priority": "高",
            "dueAt": "2026-01-02",
        }
    )


def assign_payload(
    machine_id: str = "SEM-A-001", recipe_id: str = "SEM-R1"
) -> AssignDispatchPayload:
    return AssignDispatchPayload.model_validate(
        {
            "machineId": machine_id,
            "recipeId": recipe_id,
            "scheduledStart": "2026-01-01 09:00",
            "scheduledEnd": "2026-01-01 10:00",
        }
    )


async def test_strategy_ordering_and_machine_matching() -> None:
    rows = [
        dispatch("D-2", priority="低", due_at="2026-01-03", item="IV"),
        dispatch("D-1", priority="高", due_at="2026-01-05", item="SEM"),
        dispatch("D-3", priority="中", due_at="2026-01-01", item="SEM"),
    ]

    assert [d.dispatch_id for d in _order_by_strategy(rows, "FIFO")] == ["D-1", "D-2", "D-3"]
    assert [d.dispatch_id for d in _order_by_strategy(rows, "Priority First")] == [
        "D-1",
        "D-3",
        "D-2",
    ]
    assert [d.dispatch_id for d in _order_by_strategy(rows, "Earliest Due Date")] == [
        "D-3",
        "D-2",
        "D-1",
    ]
    assert [d.dispatch_id for d in _order_by_strategy(rows, "Least Setup Change")] == [
        "D-2",
        "D-1",
        "D-3",
    ]
    assert [d.dispatch_id for d in _order_by_strategy(rows, "Hybrid")] == ["D-1", "D-3", "D-2"]
    assert _match_machine("SEM", [machine("M-1", items=["IV"]), machine("M-2")]) == "M-2"
    assert _match_machine("FIB", [machine("M-1")]) is None


async def test_create_dispatch_success_duplicate_missing_and_cross_lab() -> None:
    repo = FakeDispatchRepo()
    repo.wips["WIP-1"] = wip("WIP-1")
    svc = DispatchService(repo, LAB_SCOPE)

    result = await svc.create(create_payload(), "Alice")
    assert result["dispatchId"] == "D-1"
    assert result["status"] == STATUS_PENDING
    assert repo.wips["WIP-1"].status == "waiting_schedule"
    assert repo.history[-1].action == "送入待排程"
    assert repo.commits == 1

    with pytest.raises(ConflictError):
        await svc.create(create_payload(), "Alice")
    with pytest.raises(NotFoundError):
        await svc.create(create_payload("D-2", "missing"), "Alice")
    repo.wips["WIP-B"] = wip("WIP-B", lab_name="電性測試實驗室")
    with pytest.raises(ForbiddenError):
        await svc.create(create_payload("D-3", "WIP-B"), "Alice")


async def test_list_suggest_and_replan_scoped_and_validate_strategy() -> None:
    repo = FakeDispatchRepo()
    repo.dispatches = {
        "D-1": dispatch("D-1", priority="高", item="SEM"),
        "D-2": dispatch("D-2", priority="低", item="IV"),
        "D-B": dispatch("D-B", lab="LAB-B"),
    }
    for d in repo.dispatches.values():
        repo.wips[d.wip_id] = wip(d.wip_id, status="waiting_schedule")
    repo.machines = {
        "SEM": machine("SEM-A-001", items=["SEM"]),
        "IV": machine("IV-A-001", items=["IV"]),
    }
    svc = DispatchService(repo, LAB_SCOPE)

    assert [d["dispatchId"] for d in await svc.list_dispatches()] == ["D-1", "D-2"]
    assert await DispatchService(repo, NO_LAB_SCOPE).list_dispatches() == []

    suggested = await svc.suggest("Priority First")
    assert [d["dispatchId"] for d in suggested] == ["D-1", "D-2"]
    assert repo.dispatches["D-1"].suggested_machine_id == "SEM-A-001"
    assert repo.dispatches["D-2"].status == STATUS_SCHEDULING

    replanned = await svc.replan("rush", "Least Setup Change")
    assert {d["replanReason"] for d in replanned} == {"rush"}
    assert repo.commits == 2

    with pytest.raises(ValidationError):
        await svc.suggest("Bad Strategy")


async def test_assign_success_and_validation_errors() -> None:
    repo = FakeDispatchRepo()
    repo.dispatches["D-1"] = dispatch("D-1", status=STATUS_SCHEDULING)
    repo.wips["WIP-D-1"] = wip("WIP-D-1", status="scheduled")
    repo.machines["SEM-A-001"] = machine("SEM-A-001", items=["SEM"])
    repo.recipes["SEM-R1"] = recipe("SEM-R1", item="SEM", machine_ids=["SEM-A-001"])
    svc = DispatchService(repo, LAB_SCOPE)

    result = await svc.assign("D-1", assign_payload(), "Bob")
    assert result["status"] == STATUS_WAITING_LOAD
    assert result["assignedMachineId"] == "SEM-A-001"
    assert repo.wips["WIP-D-1"].status == "dispatched"
    assert repo.history[-1].action == "派工指派"

    repo.dispatches["not-ready"] = dispatch("not-ready", status=STATUS_PENDING)
    with pytest.raises(ConflictError):
        await svc.assign("not-ready", assign_payload(), "Bob")
    with pytest.raises(NotFoundError):
        await svc.assign("missing", assign_payload(), "Bob")

    repo.dispatches["D-2"] = dispatch("D-2", status=STATUS_SCHEDULING)
    with pytest.raises(NotFoundError):
        await svc.assign("D-2", assign_payload("missing", "SEM-R1"), "Bob")

    repo.machines["IV-B-001"] = machine("IV-B-001", lab="LAB-B", items=["SEM"])
    with pytest.raises(NotFoundError):
        await svc.assign("D-2", assign_payload("IV-B-001", "SEM-R1"), "Bob")

    repo.machines["IV-A-001"] = machine("IV-A-001", items=["IV"])
    with pytest.raises(ValidationError):
        await svc.assign("D-2", assign_payload("IV-A-001", "SEM-R1"), "Bob")

    with pytest.raises(NotFoundError):
        await svc.assign("D-2", assign_payload("SEM-A-001", "missing"), "Bob")

    repo.recipes["IV-R1"] = recipe("IV-R1", item="IV", machine_ids=["SEM-A-001"])
    with pytest.raises(ValidationError):
        await svc.assign("D-2", assign_payload("SEM-A-001", "IV-R1"), "Bob")

    repo.recipes["SEM-R2"] = recipe("SEM-R2", item="SEM", machine_ids=["OTHER"])
    with pytest.raises(ValidationError):
        await svc.assign("D-2", assign_payload("SEM-A-001", "SEM-R2"), "Bob")


async def test_sync_wip_status_forward_only_and_strict_conflict() -> None:
    repo = FakeDispatchRepo()
    svc = DispatchService(repo, LAB_SCOPE)

    repo.wips["ahead"] = wip("ahead", status="dispatched")
    await svc._sync_wip_status("ahead", "scheduled", "排程", "skip", "system")
    assert repo.wips["ahead"].status == "dispatched"
    assert repo.history == []

    repo.wips["missing"] = None  # type: ignore[assignment]
    await svc._sync_wip_status("missing", "scheduled", "排程", "skip", "system")
    assert repo.history == []

    repo.wips["running"] = wip("running", status="running")
    await svc._sync_wip_status("running", "scheduled", "排程", "skip", "system")
    assert repo.wips["running"].status == "running"

    with pytest.raises(ConflictError):
        await svc._sync_wip_status(
            "running", "dispatched", "派工指派", "strict", "system", strict=True
        )

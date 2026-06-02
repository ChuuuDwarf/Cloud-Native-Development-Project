from __future__ import annotations

import pytest

from app.common.dependencies.lab_scope import LabScope
from app.common.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.db.models import Machine
from app.modules.machines.schemas import MachinePayload
from app.modules.machines.service import DEFAULT_STATUS, MachineService

pytestmark = pytest.mark.asyncio


LAB_SCOPE = LabScope(role="lab_engineer", lab_name="材料分析實驗室", lab_code="LAB-A")
NO_LAB_SCOPE = LabScope(role="lab_engineer", lab_name=None, lab_code=None)


class FakeMachineRepo:
    def __init__(self) -> None:
        self.machines: dict[str, Machine] = {}
        self.added: list[Machine] = []
        self.commits = 0
        self.last_list_lab: str | None = None

    async def list_machines(self, lab_name: str | None = None) -> list[Machine]:
        self.last_list_lab = lab_name
        rows = list(self.machines.values())
        return [m for m in rows if lab_name is None or m.lab == lab_name]

    async def get_by_machine_id(self, machine_id: str) -> Machine | None:
        return self.machines.get(machine_id)

    def add(self, machine: Machine) -> None:
        self.added.append(machine)
        self.machines[machine.machine_id] = machine

    async def commit(self) -> None:
        self.commits += 1


def payload(machine_id: str = "M-1", **overrides: object) -> MachinePayload:
    data = {
        "machineId": machine_id,
        "name": "SEM 機台",
        "lab": "LAB-A",
        "supportedItems": ["SEM"],
        "owner": "Alice",
        "utilization": 20,
        "lastMaintenance": "2026-01-01",
    }
    data.update(overrides)
    return MachinePayload.model_validate(data)


def machine(machine_id: str = "M-1", lab: str = "LAB-A", status: str = "閒置") -> Machine:
    return Machine(
        machine_id=machine_id,
        name="SEM 機台",
        lab=lab,
        status=status,
        supported_items=["SEM"],
        owner="Alice",
        utilization=20,
        last_maintenance="2026-01-01",
    )


async def test_list_machines_scopes_by_lab_and_no_lab_scope_returns_empty() -> None:
    repo = FakeMachineRepo()
    repo.machines = {"A": machine("A", "LAB-A"), "B": machine("B", "LAB-B")}

    assert [m["machineId"] for m in await MachineService(repo, LAB_SCOPE).list_machines()] == ["A"]
    assert repo.last_list_lab == "LAB-A"
    assert await MachineService(repo, NO_LAB_SCOPE).list_machines() == []


async def test_create_machine_defaults_status_and_commits() -> None:
    repo = FakeMachineRepo()
    result = await MachineService(repo, LAB_SCOPE).create(payload("M-new"))

    assert result["machineId"] == "M-new"
    assert result["status"] == DEFAULT_STATUS
    assert repo.commits == 1
    assert repo.added[0].supported_items == ["SEM"]


async def test_create_machine_rejects_cross_lab_duplicate_and_invalid_status() -> None:
    repo = FakeMachineRepo()
    repo.machines["M-existing"] = machine("M-existing", "LAB-A")
    svc = MachineService(repo, LAB_SCOPE)

    with pytest.raises(ForbiddenError):
        await svc.create(payload("M-x", lab="LAB-B"))
    with pytest.raises(ConflictError):
        await svc.create(payload("M-existing"))
    with pytest.raises(ValidationError):
        await svc.create(payload("M-bad", status="壞掉"))


async def test_update_preserves_status_unless_payload_supplies_one() -> None:
    repo = FakeMachineRepo()
    repo.machines["M-1"] = machine("M-1", status="使用中")
    svc = MachineService(repo, LAB_SCOPE)

    result = await svc.update("M-1", payload("M-1", name="更新名稱"))
    assert result["name"] == "更新名稱"
    assert result["status"] == "使用中"

    result = await svc.update("M-1", payload("M-1", status="保養中"))
    assert result["status"] == "保養中"
    assert repo.commits == 2


async def test_update_and_status_enforce_scope_missing_and_valid_status() -> None:
    repo = FakeMachineRepo()
    repo.machines = {"A": machine("A", "LAB-A"), "B": machine("B", "LAB-B")}
    svc = MachineService(repo, LAB_SCOPE)

    with pytest.raises(NotFoundError):
        await svc.update("missing", payload("missing"))
    with pytest.raises(NotFoundError):
        await svc.update("B", payload("B", lab="LAB-B"))
    with pytest.raises(ForbiddenError):
        await svc.update("A", payload("A", lab="LAB-B"))
    with pytest.raises(ValidationError):
        await svc.update_status("A", "未知")

    result = await svc.update_status("A", "停用")
    assert result["status"] == "停用"
    assert repo.commits == 1

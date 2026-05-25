"""機台管理商業邏輯：建立 / 更新 / 狀態切換。

Status values are stored verbatim in Chinese:
    閒置 / 使用中 / 保養中 / 故障中 / 停用 (新建預設為「閒置」)
"""

from __future__ import annotations

from app.common.errors import ConflictError, NotFoundError, ValidationError
from app.db.models import Machine
from app.modules.machines.repository import MachineRepository
from app.modules.machines.schemas import MachinePayload
from app.modules.machines.serializers import machine_dict

VALID_STATUSES = {"閒置", "使用中", "保養中", "故障中", "停用"}
DEFAULT_STATUS = "閒置"


class MachineService:
    def __init__(self, repo: MachineRepository) -> None:
        self._repo = repo

    async def list_machines(self) -> list[dict]:
        machines = await self._repo.list_machines()
        return [machine_dict(m) for m in machines]

    async def _require(self, machine_id: str) -> Machine:
        machine = await self._repo.get_by_machine_id(machine_id)
        if machine is None:
            raise NotFoundError(f"找不到機台：{machine_id}")
        return machine

    async def create(self, payload: MachinePayload) -> dict:
        if await self._repo.get_by_machine_id(payload.machine_id) is not None:
            raise ConflictError(f"機台編號已存在：{payload.machine_id}")
        machine = Machine(
            machine_id=payload.machine_id,
            name=payload.name,
            lab=payload.lab,
            status=DEFAULT_STATUS,
            supported_items=list(payload.supported_items),
            owner=payload.owner,
            utilization=payload.utilization,
            last_maintenance=payload.last_maintenance,
        )
        self._repo.add(machine)
        await self._repo.commit()
        return machine_dict(machine)

    async def update(self, machine_id: str, payload: MachinePayload) -> dict:
        machine = await self._require(machine_id)
        machine.name = payload.name
        machine.lab = payload.lab
        machine.supported_items = list(payload.supported_items)
        machine.owner = payload.owner
        machine.utilization = payload.utilization
        machine.last_maintenance = payload.last_maintenance
        await self._repo.commit()
        return machine_dict(machine)

    async def update_status(self, machine_id: str, status: str) -> dict:
        if status not in VALID_STATUSES:
            raise ValidationError(
                f"無效的機台狀態：{status}（需為 {'/'.join(sorted(VALID_STATUSES))}）"
            )
        machine = await self._require(machine_id)
        machine.status = status
        await self._repo.commit()
        return machine_dict(machine)

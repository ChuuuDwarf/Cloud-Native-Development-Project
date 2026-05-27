"""機台管理商業邏輯：建立 / 更新 / 狀態切換。

Status values are stored verbatim in Chinese:
    閒置 / 使用中 / 保養中 / 故障中 / 停用 (新建預設為「閒置」)

Lab scoping: non-admin callers only see / mutate machines in their own lab.
See ``app.common.dependencies.lab_scope.LabScope`` for the rule matrix.
"""

from __future__ import annotations

from app.common.dependencies.lab_scope import LabScope
from app.common.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.db.models import Machine
from app.modules.machines.repository import MachineRepository
from app.modules.machines.schemas import MachinePayload
from app.modules.machines.serializers import machine_dict

VALID_STATUSES = {"閒置", "使用中", "保養中", "故障中", "停用"}
DEFAULT_STATUS = "閒置"


class MachineService:
    def __init__(self, repo: MachineRepository, scope: LabScope) -> None:
        self._repo = repo
        self._scope = scope

    async def list_machines(self) -> list[dict]:
        if self._scope.restricted_without_lab:
            return []
        # Machines table stores lab as short code (e.g. "LAB-A"), not display name.
        machines = await self._repo.list_machines(lab_name=self._scope.list_lab_code_filter())
        return [machine_dict(m) for m in machines]

    async def _require(self, machine_id: str) -> Machine:
        machine = await self._repo.get_by_machine_id(machine_id)
        if machine is None:
            raise NotFoundError(f"找不到機台：{machine_id}")
        # Don't leak existence of other labs' machines — same 404, not 403.
        if not self._scope.can_access_lab(machine.lab):
            raise NotFoundError(f"找不到機台：{machine_id}")
        return machine

    async def create(self, payload: MachinePayload) -> dict:
        # Non-admins can only create machines in their own lab.
        if not self._scope.can_access_lab(payload.lab):
            raise ForbiddenError(f"無權限在實驗室 {payload.lab} 建立機台")
        existing = await self._repo.get_by_machine_id(payload.machine_id)
        if existing is not None:
            raise ConflictError(
                f"機台編號 {payload.machine_id} 已存在於 {existing.lab or '未指定'} 實驗室"
            )
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
        # Block moving a machine into a lab the caller can't access.
        if not self._scope.can_access_lab(payload.lab):
            raise ForbiddenError(f"無權限將機台移至實驗室 {payload.lab}")
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

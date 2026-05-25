"""HTTP routes for /api/machines. Owned by 組員 C.

Thin router — all logic lives in :class:`MachineService`. Matches the frontend
client ``frontend/src/services/machines-api.ts``.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.common.dependencies import CurrentUser, get_current_user, require_permission
from app.common.schemas import ApiResponse, PageResponse
from app.modules.machines.dependencies import get_machine_service
from app.modules.machines.schemas import MachinePayload, MachineStatusBody
from app.modules.machines.service import MachineService

router = APIRouter(prefix="/api/machines", tags=["Machines"])

MACHINES_READ = "machines:read"
MACHINES_MANAGE = "machines:manage"


@router.get("", response_model=PageResponse[dict])
async def list_machines(
    service: Annotated[MachineService, Depends(get_machine_service)],
    _: Annotated[CurrentUser, Depends(get_current_user)],
) -> PageResponse[dict]:
    items = await service.list_machines()
    return PageResponse(items=items, page=1, page_size=len(items), total=len(items))


@router.post("", response_model=ApiResponse[dict])
async def create_machine(
    body: MachinePayload,
    service: Annotated[MachineService, Depends(get_machine_service)],
    _: Annotated[CurrentUser, Depends(require_permission(MACHINES_MANAGE))],
) -> ApiResponse[dict]:
    return ApiResponse(data=await service.create(body), message="機台已建立")


@router.patch("/{machine_id}", response_model=ApiResponse[dict])
async def update_machine(
    machine_id: str,
    body: MachinePayload,
    service: Annotated[MachineService, Depends(get_machine_service)],
    _: Annotated[CurrentUser, Depends(require_permission(MACHINES_MANAGE))],
) -> ApiResponse[dict]:
    return ApiResponse(data=await service.update(machine_id, body), message="機台已更新")


@router.patch("/{machine_id}/status", response_model=ApiResponse[dict])
async def update_machine_status(
    machine_id: str,
    body: MachineStatusBody,
    service: Annotated[MachineService, Depends(get_machine_service)],
    _: Annotated[CurrentUser, Depends(require_permission(MACHINES_MANAGE))],
) -> ApiResponse[dict]:
    return ApiResponse(
        data=await service.update_status(machine_id, body.status),
        message="機台狀態已更新",
    )

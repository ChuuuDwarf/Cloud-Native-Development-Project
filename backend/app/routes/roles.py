"""HTTP routes for /api/roles and /api/permissions."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.common.dependencies import CurrentUser, get_current_user
from app.common.schemas import PageResponse
from app.schemas.roles import PermissionResponse, RoleResponse
from app.services.roles import RoleService, get_role_service

router = APIRouter(prefix="/api", tags=["Roles"])


@router.get("/roles", response_model=PageResponse[RoleResponse])
async def list_roles(
    service: Annotated[RoleService, Depends(get_role_service)],
    _: Annotated[CurrentUser, Depends(get_current_user)],
) -> PageResponse[RoleResponse]:
    roles = await service.list_roles()
    items = [RoleResponse.model_validate(r) for r in roles]
    return PageResponse[RoleResponse](items=items, total=len(items), page=1, pageSize=len(items))


@router.get("/permissions", response_model=PageResponse[PermissionResponse])
async def list_permissions(
    service: Annotated[RoleService, Depends(get_role_service)],
    _: Annotated[CurrentUser, Depends(get_current_user)],
) -> PageResponse[PermissionResponse]:
    permissions = await service.list_permissions()
    items = [PermissionResponse.model_validate(p) for p in permissions]
    return PageResponse[PermissionResponse](
        items=items, total=len(items), page=1, pageSize=len(items)
    )

"""HTTP routes for /api/users."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.common.dependencies import (
    CurrentUser,
    PaginationParams,
    get_current_user,
    get_pagination,
    require_permission,
)
from app.common.enums import UserStatus
from app.common.schemas import ApiResponse, PageResponse
from app.modules.users.dependencies import get_user_service
from app.modules.users.schemas import (
    UserCreate,
    UserQuery,
    UserResponse,
    UserUpdate,
)
from app.modules.users.service import UserService

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("", response_model=PageResponse[UserResponse])
async def get_users(
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    service: Annotated[UserService, Depends(get_user_service)],
    _: Annotated[CurrentUser, Depends(require_permission("users:read"))],
    keyword: str | None = Query(default=None),
    role: str | None = Query(default=None),
    department_id: uuid.UUID | None = Query(default=None, alias="departmentId"),
    lab_id: uuid.UUID | None = Query(default=None, alias="labId"),
    user_status: UserStatus | None = Query(default=None, alias="status"),
) -> PageResponse[UserResponse]:
    query = UserQuery(
        keyword=keyword,
        role=role,
        departmentId=department_id,
        labId=lab_id,
        status=user_status,
    )
    users, total = await service.find_users(
        offset=pagination.offset,
        limit=pagination.page_size,
        query=query,
    )
    return PageResponse[UserResponse](
        items=[UserResponse.model_validate(u) for u in users],
        page=pagination.page,
        pageSize=pagination.page_size,
        total=total,
    )


@router.post(
    "",
    response_model=ApiResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    payload: UserCreate,
    service: Annotated[UserService, Depends(get_user_service)],
    _: Annotated[CurrentUser, Depends(require_permission("users:create"))],
) -> ApiResponse[UserResponse]:
    created = await service.create_user(payload)
    return ApiResponse(data=UserResponse.model_validate(created), message="created")


@router.get("/{user_id}", response_model=ApiResponse[UserResponse])
async def get_user_by_id(
    user_id: uuid.UUID,
    service: Annotated[UserService, Depends(get_user_service)],
    _: Annotated[CurrentUser, Depends(get_current_user)],
) -> ApiResponse[UserResponse]:
    user = await service.find_user_by_id(user_id)
    return ApiResponse(data=UserResponse.model_validate(user))


@router.patch("/{user_id}", response_model=ApiResponse[UserResponse])
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    service: Annotated[UserService, Depends(get_user_service)],
    _: Annotated[CurrentUser, Depends(require_permission("users:update"))],
) -> ApiResponse[UserResponse]:
    updated = await service.update_user(user_id, payload)
    return ApiResponse(data=UserResponse.model_validate(updated), message="updated")

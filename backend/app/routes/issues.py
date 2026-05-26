"""HTTP routes for /api/issues."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.common.dependencies import (
    CurrentUser,
    PaginationParams,
    get_pagination,
    require_permission,
)
from app.common.enums import IssueStatus, IssueType, Severity
from app.common.schemas import ApiResponse, PageResponse
from app.schemas.issues import (
    IssueCreate,
    IssueListParams,
    IssueRead,
    IssueUpdate,
)
from app.services.issues import IssueService, get_issue_service

router = APIRouter(prefix="/api/issues", tags=["Issues"])


@router.post("", response_model=ApiResponse[IssueRead], status_code=status.HTTP_201_CREATED)
async def create_issue(
    payload: IssueCreate,
    service: Annotated[IssueService, Depends(get_issue_service)],
    user: Annotated[CurrentUser, Depends(require_permission("issues:create"))],
) -> ApiResponse[IssueRead]:
    created = await service.create_issue(payload, user)
    return ApiResponse(data=IssueRead.model_validate(created), message="created")


@router.get("", response_model=PageResponse[IssueRead])
async def list_issues(
    pagination: Annotated[PaginationParams, Depends(get_pagination)],
    service: Annotated[IssueService, Depends(get_issue_service)],
    user: Annotated[CurrentUser, Depends(require_permission("issues:read"))],
    status_filter: IssueStatus | None = Query(default=None, alias="status"),
    severity: Severity | None = Query(default=None),
    type_filter: IssueType | None = Query(default=None, alias="type"),
    assigned_to: UUID | None = Query(default=None, alias="assignedTo"),
    target_type: str | None = Query(default=None, alias="targetType"),
) -> PageResponse[IssueRead]:
    params = IssueListParams(
        status=status_filter,
        severity=severity,
        type=type_filter,
        assignedTo=assigned_to,
        targetType=target_type,
        page=pagination.page,
        pageSize=pagination.page_size,
    )
    items, total = await service.list_issues(params, user)
    return PageResponse[IssueRead](
        items=[IssueRead.model_validate(i) for i in items],
        page=pagination.page,
        pageSize=pagination.page_size,
        total=total,
    )


@router.get("/{issue_id}", response_model=ApiResponse[IssueRead])
async def get_issue(
    issue_id: UUID,
    service: Annotated[IssueService, Depends(get_issue_service)],
    user: Annotated[CurrentUser, Depends(require_permission("issues:read"))],
) -> ApiResponse[IssueRead]:
    issue = await service.get_issue(issue_id, user)
    return ApiResponse(data=IssueRead.model_validate(issue))


@router.patch("/{issue_id}", response_model=ApiResponse[IssueRead])
async def update_issue(
    issue_id: UUID,
    payload: IssueUpdate,
    service: Annotated[IssueService, Depends(get_issue_service)],
    user: Annotated[CurrentUser, Depends(require_permission("issues:update"))],
) -> ApiResponse[IssueRead]:
    updated = await service.update_issue(issue_id, payload, user)
    return ApiResponse(data=IssueRead.model_validate(updated), message="updated")

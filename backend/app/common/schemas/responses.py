"""Shared response envelopes per docs/development_standards.md §6.2.

Usage::

    from app.common.schemas import ApiResponse, PageResponse, ErrorResponse

    @router.get("", response_model=PageResponse[UserResponse])
    async def list_users(...) -> PageResponse[UserResponse]:
        return PageResponse(items=..., page=1, page_size=20, total=...)
"""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    data: T
    message: str = "success"


class PageResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(populate_by_name=True)

    items: list[T]
    page: int = 1
    page_size: int = Field(20, alias="pageSize")
    total: int = 0


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail

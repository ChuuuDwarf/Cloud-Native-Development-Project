"""實驗報告 API：/api/reports。

狀態流程：草稿→待審核→已確認→已發布/已回傳→已改版。
建立/編輯/送審/發布由實驗室人員，審核由主管。

Ported from Role D's flat ``app/routers/reports.py``. Thin router — all logic
lives in :class:`ReportService`.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.common.dependencies import CurrentUser, get_current_user, require_permission
from app.common.schemas import ApiResponse, PageResponse
from app.modules.reports.dependencies import get_report_service
from app.modules.reports.schemas import ReportCreateBody, ReportEditBody, ReportReviewBody
from app.modules.reports.service import ReportService

router = APIRouter(prefix="/api/reports", tags=["Reports"])

REPORTS_OPERATE = "reports:operate"
REPORTS_REVIEW = "reports:review"


@router.get("", response_model=PageResponse[dict])
async def list_reports(
    service: Annotated[ReportService, Depends(get_report_service)],
    _: Annotated[CurrentUser, Depends(get_current_user)],
    status: str | None = None,
    order_id: str | None = None,
) -> PageResponse[dict]:
    items = await service.list_reports(status, order_id)
    return PageResponse(items=items, page=1, page_size=len(items), total=len(items))


@router.get("/{report_id}", response_model=ApiResponse[dict])
async def get_report(
    report_id: str,
    service: Annotated[ReportService, Depends(get_report_service)],
    _: Annotated[CurrentUser, Depends(get_current_user)],
) -> ApiResponse[dict]:
    """報告詳情，含版本紀錄。"""
    return ApiResponse(data=await service.get_report(report_id))


@router.post("", response_model=ApiResponse[dict])
async def create_report(
    body: ReportCreateBody,
    service: Annotated[ReportService, Depends(get_report_service)],
    user: Annotated[CurrentUser, Depends(require_permission(REPORTS_OPERATE))],
) -> ApiResponse[dict]:
    return ApiResponse(
        data=await service.create_report(body.wip_id, user.name),
        message="已建立報告草稿",
    )


@router.patch("/{report_id}", response_model=ApiResponse[dict])
async def edit_report(
    report_id: str,
    body: ReportEditBody,
    service: Annotated[ReportService, Depends(get_report_service)],
    _: Annotated[CurrentUser, Depends(require_permission(REPORTS_OPERATE))],
) -> ApiResponse[dict]:
    return ApiResponse(
        data=await service.edit_report(
            report_id, body.summary, body.conclusion, body.attachment_name
        ),
        message="報告已更新",
    )


@router.post("/{report_id}/submit", response_model=ApiResponse[dict])
async def submit_report(
    report_id: str,
    service: Annotated[ReportService, Depends(get_report_service)],
    user: Annotated[CurrentUser, Depends(require_permission(REPORTS_OPERATE))],
) -> ApiResponse[dict]:
    return ApiResponse(
        data=await service.submit_report(report_id, user.name),
        message="已提交審核",
    )


@router.post("/{report_id}/review", response_model=ApiResponse[dict])
async def review_report(
    report_id: str,
    body: ReportReviewBody,
    service: Annotated[ReportService, Depends(get_report_service)],
    user: Annotated[CurrentUser, Depends(require_permission(REPORTS_REVIEW))],
) -> ApiResponse[dict]:
    return ApiResponse(
        data=await service.review_report(report_id, body.approve, body.comment, user.name),
        message="報告已確認" if body.approve else "報告已退回",
    )


@router.post("/{report_id}/publish", response_model=ApiResponse[dict])
async def publish_report(
    report_id: str,
    service: Annotated[ReportService, Depends(get_report_service)],
    user: Annotated[CurrentUser, Depends(require_permission(REPORTS_OPERATE))],
) -> ApiResponse[dict]:
    """發布並回傳使用者（主管確認後，由人員或主管發布）。"""
    return ApiResponse(
        data=await service.publish_report(report_id, user.name),
        message="報告已發布並回傳使用者",
    )


"""實驗執行 API：/api/experiment-runs。

涵蓋上機/下機登記、進度、結果上傳、結果確認、中止申請與主管審核，
以及機台自動完成訊號（觸發 Celery 背景任務處理）。

Ported from Role D's flat ``app/routers/experiments.py``. Thin router — all
logic lives in :class:`ExperimentRunService`.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.common.dependencies import CurrentUser, get_current_user, require_permission
from app.common.schemas import ApiResponse, PageResponse
from app.modules.experiment_runs.dependencies import get_experiment_run_service
from app.modules.experiment_runs.schemas import (
    AbortRequestBody,
    AbortReviewBody,
    CheckInRequest,
    CheckOutRequest,
    ProgressRequest,
    ResultRequest,
)
from app.modules.experiment_runs.service import ExperimentRunService

router = APIRouter(prefix="/api/experiment-runs", tags=["ExperimentRuns"])

EXPERIMENTS_OPERATE = "experiments:operate"
EXPERIMENTS_REVIEW = "experiments:review"


@router.get("", response_model=PageResponse[dict])
async def list_experiment_runs(
    service: Annotated[ExperimentRunService, Depends(get_experiment_run_service)],
    _: Annotated[CurrentUser, Depends(get_current_user)],
    status: str | None = None,
) -> PageResponse[dict]:
    """列出實驗執行中的 WIP，可用 status 過濾。"""
    items = await service.list_wips(status)
    return PageResponse(items=items, page=1, page_size=len(items), total=len(items))


@router.get("/{wip_id}", response_model=ApiResponse[dict])
async def get_experiment_run(
    wip_id: str,
    service: Annotated[ExperimentRunService, Depends(get_experiment_run_service)],
    _: Annotated[CurrentUser, Depends(get_current_user)],
) -> ApiResponse[dict]:
    """查詢單一 WIP，含完整機台履歷。"""
    return ApiResponse(data=await service.get_wip(wip_id))


@router.post("/{wip_id}/check-in", response_model=ApiResponse[dict])
async def check_in(
    wip_id: str,
    body: CheckInRequest,
    service: Annotated[ExperimentRunService, Depends(get_experiment_run_service)],
    _: Annotated[CurrentUser, Depends(require_permission(EXPERIMENTS_OPERATE))],
) -> ApiResponse[dict]:
    return ApiResponse(
        data=await service.check_in(wip_id, body.operator, body.machine_id, body.recipe),
        message="上機登記完成",
    )


@router.post("/{wip_id}/check-out", response_model=ApiResponse[dict])
async def check_out(
    wip_id: str,
    body: CheckOutRequest,
    service: Annotated[ExperimentRunService, Depends(get_experiment_run_service)],
    _: Annotated[CurrentUser, Depends(require_permission(EXPERIMENTS_OPERATE))],
) -> ApiResponse[dict]:
    return ApiResponse(
        data=await service.check_out(wip_id, body.operator, body.note),
        message="下機登記完成",
    )


@router.patch("/{wip_id}/progress", response_model=ApiResponse[dict])
async def update_progress(
    wip_id: str,
    body: ProgressRequest,
    service: Annotated[ExperimentRunService, Depends(get_experiment_run_service)],
    _: Annotated[CurrentUser, Depends(require_permission(EXPERIMENTS_OPERATE))],
) -> ApiResponse[dict]:
    return ApiResponse(
        data=await service.update_progress(wip_id, body.progress),
        message="進度已更新",
    )


@router.post("/{wip_id}/result", response_model=ApiResponse[dict])
async def upload_result(
    wip_id: str,
    body: ResultRequest,
    service: Annotated[ExperimentRunService, Depends(get_experiment_run_service)],
    _: Annotated[CurrentUser, Depends(require_permission(EXPERIMENTS_OPERATE))],
) -> ApiResponse[dict]:
    return ApiResponse(
        data=await service.upload_result(wip_id, body.note, body.raw_data_url, body.data_verified),
        message="結果已上傳，進入待結果確認",
    )


@router.post("/{wip_id}/confirm", response_model=ApiResponse[dict])
async def confirm_result(
    wip_id: str,
    body: CheckOutRequest,
    service: Annotated[ExperimentRunService, Depends(get_experiment_run_service)],
    _: Annotated[CurrentUser, Depends(require_permission(EXPERIMENTS_OPERATE))],
) -> ApiResponse[dict]:
    """確認結果。"""
    return ApiResponse(
        data=await service.confirm_result(wip_id, body.operator),
        message="結果已確認，標記完成",
    )


@router.post("/{wip_id}/abort-request", response_model=ApiResponse[dict])
async def abort_request(
    wip_id: str,
    body: AbortRequestBody,
    service: Annotated[ExperimentRunService, Depends(get_experiment_run_service)],
    user: Annotated[CurrentUser, Depends(require_permission(EXPERIMENTS_OPERATE))],
) -> ApiResponse[dict]:
    """提出中止申請（實驗室人員不可直接終止）。"""
    return ApiResponse(
        data=await service.request_abort(wip_id, body.reason, user.name),
        message="已提出中止申請，待主管判定",
    )


@router.post("/{wip_id}/abort-review", response_model=ApiResponse[dict])
async def abort_review(
    wip_id: str,
    body: AbortReviewBody,
    service: Annotated[ExperimentRunService, Depends(get_experiment_run_service)],
    user: Annotated[CurrentUser, Depends(require_permission(EXPERIMENTS_REVIEW))],
) -> ApiResponse[dict]:
    """主管審核中止申請。"""
    return ApiResponse(
        data=await service.review_abort(wip_id, body.approve, body.note, user.name),
        message="已核准終止" if body.approve else "已駁回，實驗繼續",
    )


@router.post("/{wip_id}/machine-signal", status_code=202, response_model=ApiResponse[dict])
async def machine_signal(
    wip_id: str,
    service: Annotated[ExperimentRunService, Depends(get_experiment_run_service)],
    _: Annotated[CurrentUser, Depends(get_current_user)],
) -> ApiResponse[dict]:
    """模擬機台回報「完成」訊號：丟給 Celery 背景任務處理。

    背景任務會自動寫入數據並把 WIP 轉「待確認」（不直接結案）。
    若 broker 未啟動（本機無 Redis），退回同步處理確保仍可展示。
    """
    # Verify WIP exists first
    await service.get_wip(wip_id)

    try:
        from app.workers.experiment_tasks import machine_complete

        task = machine_complete.delay(wip_id)
        return ApiResponse(
            data={"wipId": wip_id, "taskId": task.id, "mode": "async"},
            message="已接收機台完成訊號，數據背景處理中",
        )
    except Exception:
        # broker 不可用 → 同步退回
        await service.apply_machine_completion(wip_id)
        return ApiResponse(
            data={"wipId": wip_id, "mode": "sync"},
            message="已接收機台完成訊號（同步處理，未連線 broker）",
        )

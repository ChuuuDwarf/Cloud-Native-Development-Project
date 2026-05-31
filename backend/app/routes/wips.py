from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.current_user import build_current_user
from app.common.dependencies import CurrentUser, get_current_user
from app.core.database import get_db
from app.services import wip_service

router = APIRouter(
    prefix="/api/wips",
    tags=["wips"],
)


class WipDependencyNextRequest(BaseModel):
    sample_id: str = Field(alias="sampleId")
    order_no: str | None = Field(default=None, alias="orderNo")

    model_config = {"populate_by_name": True}


@router.post("/dependency/next")
async def claim_next_dependency_experiment(
    payload: WipDependencyNextRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await build_current_user(current_user, db)
    return await wip_service.claim_next_dependency_experiment(
        db=db,
        sample_id=payload.sample_id,
        order_no=payload.order_no,
    )


@router.get("")
async def get_wips(
    status: str | None = Query(default=None),
    include_all_for_flow: bool = Query(default=False),
    own_lab_only: bool = Query(default=False),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    wip_current_user = await build_current_user(current_user, db)
    return await wip_service.list_wips(
        db=db,
        current_user=wip_current_user,
        status=status,
        include_all_for_flow=include_all_for_flow,
        own_lab_only=own_lab_only,
    )


@router.get("/{wip_id}")
async def get_wip(
    wip_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    wip_current_user = await build_current_user(current_user, db)
    return await wip_service.get_wip_detail(
        db=db,
        current_user=wip_current_user,
        wip_id=wip_id,
    )


@router.get("/{wip_id}/history")
async def get_wip_history(
    wip_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    wip_current_user = await build_current_user(current_user, db)
    return await wip_service.list_wip_history(
        db=db,
        current_user=wip_current_user,
        wip_id=wip_id,
    )


@router.patch("/{wip_id}")
async def update_wip(
    wip_id: str,
    payload: dict,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    wip_current_user = await build_current_user(current_user, db)
    return await wip_service.update_wip(
        db=db,
        current_user=wip_current_user,
        wip_id=wip_id,
        payload=payload,
    )


@router.post("/{wip_id}/actions")
async def wip_action(
    wip_id: str,
    payload: dict,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    wip_current_user = await build_current_user(current_user, db)
    return await wip_service.handle_wip_action(
        db=db,
        current_user=wip_current_user,
        wip_id=wip_id,
        payload=payload,
    )
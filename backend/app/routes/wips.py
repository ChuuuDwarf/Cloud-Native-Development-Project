from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.current_user import build_current_user
from app.common.dependencies import CurrentUser, get_current_user
from app.core.database import get_db
from app.services import wip_service

router = APIRouter(
    prefix="/api/wips",
    tags=["wips"],
)


@router.get("")
async def get_wips(
    status: str | None = Query(default=None),
    include_all_for_flow: bool = Query(default=False),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    wip_current_user = await build_current_user(current_user, db)
    return await wip_service.list_wips(
        db=db,
        current_user=wip_current_user,
        status=status,
        include_all_for_flow=include_all_for_flow,
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

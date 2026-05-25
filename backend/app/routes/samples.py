from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.current_user import build_current_user
from app.common.dependencies import CurrentUser, get_current_user
from app.core.database import get_db
from app.services import sample_service

router = APIRouter(
    prefix="/api/samples",
    tags=["samples"],
)


@router.get("")
async def get_samples(
    status: str | None = Query(default=None),
    scope: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sample_current_user = await build_current_user(current_user, db)
    return await sample_service.list_samples(
        db=db,
        current_user=sample_current_user,
        status=status,
        scope=scope,
    )


@router.get("/{sample_id}")
async def get_sample(
    sample_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sample_current_user = await build_current_user(current_user, db)
    return await sample_service.get_sample_detail(
        db=db,
        current_user=sample_current_user,
        sample_id=sample_id,
    )


@router.get("/{sample_id}/history")
async def get_sample_history(
    sample_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sample_current_user = await build_current_user(current_user, db)
    return await sample_service.list_sample_history(
        db=db,
        current_user=sample_current_user,
        sample_id=sample_id,
    )


@router.patch("/{sample_id}")
async def update_sample(
    sample_id: str,
    payload: dict,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sample_current_user = await build_current_user(current_user, db)
    return await sample_service.update_sample(
        db=db,
        current_user=sample_current_user,
        sample_id=sample_id,
        payload=payload,
    )


@router.post("/{sample_id}/actions")
async def sample_action(
    sample_id: str,
    payload: dict,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sample_current_user = await build_current_user(current_user, db)
    return await sample_service.handle_sample_action(
        db=db,
        current_user=sample_current_user,
        sample_id=sample_id,
        payload=payload,
    )

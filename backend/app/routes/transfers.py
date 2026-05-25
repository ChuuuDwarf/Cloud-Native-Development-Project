from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.current_user import build_current_user
from app.common.dependencies import CurrentUser, get_current_user
from app.core.database import get_db
from app.services import transfer_service

router = APIRouter(
    prefix="/api/transfers",
    tags=["transfers"],
)


@router.get("")
async def get_transfers(
    db: AsyncSession = Depends(get_db),
    auth_user: CurrentUser = Depends(get_current_user),
):
    current_user = await build_current_user(auth_user, db)
    return await transfer_service.list_transfers(
        db=db,
        current_user=current_user,
    )


@router.post("")
async def create_transfer(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    auth_user: CurrentUser = Depends(get_current_user),
):
    current_user = await build_current_user(auth_user, db)
    return await transfer_service.create_transfer(
        db=db,
        current_user=current_user,
        payload=payload,
    )


@router.post("/{transfer_id}/actions")
async def transfer_action(
    transfer_id: str,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    auth_user: CurrentUser = Depends(get_current_user),
):
    current_user = await build_current_user(auth_user, db)
    return await transfer_service.handle_transfer_action(
        db=db,
        current_user=current_user,
        transfer_id=transfer_id,
        payload=payload,
    )

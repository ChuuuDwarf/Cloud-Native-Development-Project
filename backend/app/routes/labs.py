from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import CurrentUser, get_current_user
from app.core.database import get_db
from app.services.labs import LabService

router = APIRouter(prefix="/api/labs", tags=["Labs"])


@router.get("")
async def list_labs(
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict:
    service = LabService(session)
    items = await service.list_active_labs()
    return {"items": items, "total": len(items)}

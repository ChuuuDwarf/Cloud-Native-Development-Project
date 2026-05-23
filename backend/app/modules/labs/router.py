"""HTTP routes for /api/labs."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import CurrentUser, get_current_user
from app.core.database import get_db
from app.db.models import Lab

router = APIRouter(prefix="/api/labs", tags=["Labs"])


@router.get("")
async def list_labs(
    session: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict:
    labs = (
        (await session.execute(select(Lab).where(Lab.is_active.is_(True)).order_by(Lab.code)))
        .scalars()
        .all()
    )
    items = [
        {"id": str(lab.id), "code": lab.code, "name": lab.name, "capacity": lab.capacity}
        for lab in labs
    ]
    return {"items": items, "total": len(items)}

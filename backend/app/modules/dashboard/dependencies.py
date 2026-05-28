"""DI shim for the dashboard module.

Kept thin — the service has no state beyond the AsyncSession, so this is
just the standard ``Depends(get_db) → Service(session)`` factory that other
modules use.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.dashboard.service import DashboardService


async def get_dashboard_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardService:
    return DashboardService(session)

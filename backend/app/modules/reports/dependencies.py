"""FastAPI dependencies for the reports module."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import CurrentUser, get_current_user
from app.common.dependencies.lab_scope import build_lab_scope
from app.core.database import get_db
from app.modules.reports.repository import ReportRepository
from app.modules.reports.service import ReportService


async def get_report_service(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> ReportService:
    scope = await build_lab_scope(user, session)
    return ReportService(ReportRepository(session), scope)

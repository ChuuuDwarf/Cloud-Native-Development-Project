"""FastAPI dependencies for the reports module."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.reports.repository import ReportRepository
from app.modules.reports.service import ReportService


def get_report_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ReportService:
    return ReportService(ReportRepository(session))

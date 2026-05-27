"""FastAPI dependencies for the experiment-runs module."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import CurrentUser, get_current_user
from app.common.dependencies.lab_scope import build_lab_scope
from app.core.database import get_db
from app.modules.experiment_runs.repository import ExperimentRunRepository
from app.modules.experiment_runs.service import ExperimentRunService


async def get_experiment_run_service(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> ExperimentRunService:
    scope = await build_lab_scope(user, session)
    return ExperimentRunService(ExperimentRunRepository(session), scope)

"""FastAPI dependencies for the experiment-runs module."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.experiment_runs.repository import ExperimentRunRepository
from app.modules.experiment_runs.service import ExperimentRunService


def get_experiment_run_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ExperimentRunService:
    return ExperimentRunService(ExperimentRunRepository(session))

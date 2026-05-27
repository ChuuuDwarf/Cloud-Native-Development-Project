"""Celery tasks for experiment execution.

機台完成訊號處理：背景任務接收機台回報後自動寫入數據並轉 WIP 為「待確認」。

Ported from Role D's ``app/tasks.py::machine_complete``.
"""

import asyncio
import logging

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.celery_app import celery_app
from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _task_session_factory() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Build a fresh ``NullPool`` engine + sessionmaker for the *current* event loop.

    Celery opens a new event loop per task invocation. Reusing the module-level
    pooled engine (``app.core.database``) leaks asyncpg connections bound to a
    previous, now-closed loop → ``RuntimeError: ... got Future ... attached to a
    different loop``. A per-task ``NullPool`` engine — disposed when the task
    ends — keeps every connection on the loop that created it.
    """
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool, future=True)
    session_local = async_sessionmaker(
        bind=engine, expire_on_commit=False, class_=AsyncSession, autoflush=False
    )
    return engine, session_local


@celery_app.task(name="app.workers.experiment_tasks.machine_complete")
def machine_complete(wip_id: str) -> dict:
    """機台完成訊號處理（背景執行）。

    Uses an async helper internally since the service/repository layer is async.
    """
    from app.common.dependencies.lab_scope import LabScope
    from app.modules.experiment_runs.repository import ExperimentRunRepository
    from app.modules.experiment_runs.service import ExperimentRunService

    async def _run() -> bool:
        engine, session_local = _task_session_factory()
        try:
            async with session_local() as session:
                # Machine-completion is a system signal (no user) → unrestricted scope.
                service = ExperimentRunService(ExperimentRunRepository(session), LabScope.system())
                return await service.apply_machine_completion(wip_id)
        finally:
            await engine.dispose()

    loop = asyncio.new_event_loop()
    try:
        handled = loop.run_until_complete(_run())
    finally:
        loop.close()

    return {"wipId": wip_id, "handled": handled}


@celery_app.task(name="app.workers.experiment_tasks.tick_progress")
def tick_progress() -> dict:
    """背景推進「執行中」WIP 的進度。

    每隔 ``PROGRESS_TICK_SECONDS`` 秒（由各 WIP 的 ``next_progress_at`` 排定）把進度
    +``PROGRESS_STEP_PERCENT``%；到 100% 時呼叫機台完成（→待確認）。由 Celery beat 觸發。
    """
    from datetime import datetime, timedelta

    from sqlalchemy import select

    from app.common.dependencies.lab_scope import LabScope
    from app.common.enums import WipStatus
    from app.db.models import Wip, WipExecution
    from app.modules.experiment_runs.repository import ExperimentRunRepository
    from app.modules.experiment_runs.service import (
        PROGRESS_STEP_PERCENT,
        PROGRESS_TICK_SECONDS,
        ExperimentRunService,
    )

    async def _run() -> list[str]:
        completed: list[str] = []
        engine, session_local = _task_session_factory()
        try:
            async with session_local() as session:
                now = datetime.now()
                due = await session.execute(
                    select(WipExecution.wip_no).where(
                        WipExecution.exec_status == WipStatus.RUNNING.value,
                        WipExecution.next_progress_at.is_not(None),
                        WipExecution.next_progress_at <= now,
                    )
                )
                for (wip_no,) in due.all():
                    wip = (
                        await session.execute(select(Wip).where(Wip.wip_no == wip_no))
                    ).scalar_one_or_none()
                    exec_row = await session.get(WipExecution, wip_no)
                    if wip is None or exec_row is None:
                        continue
                    new_progress = min(100, (wip.progress or 0) + PROGRESS_STEP_PERCENT)
                    wip.progress = new_progress
                    if new_progress >= 100:
                        exec_row.next_progress_at = None
                        completed.append(wip_no)
                    else:
                        exec_row.next_progress_at = now + timedelta(seconds=PROGRESS_TICK_SECONDS)
                await session.commit()

            # 100% → 機台回報完成（→待確認）；用 service 確保狀態橋接一致。
            for wip_no in completed:
                async with session_local() as s2:
                    service = ExperimentRunService(ExperimentRunRepository(s2), LabScope.system())
                    await service.apply_machine_completion(wip_no)
        finally:
            await engine.dispose()
        return completed

    loop = asyncio.new_event_loop()
    try:
        completed = loop.run_until_complete(_run())
    finally:
        loop.close()

    return {"completed": completed}

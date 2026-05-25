"""Celery tasks for experiment execution.

機台完成訊號處理：背景任務接收機台回報後自動寫入數據並轉 WIP 為「待確認」。

Ported from Role D's ``app/tasks.py::machine_complete``.
"""

import asyncio
import logging

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.experiment_tasks.machine_complete")
def machine_complete(wip_id: str) -> dict:
    """機台完成訊號處理（背景執行）。

    Uses an async helper internally since the service/repository layer is async.
    """
    from app.core.database import AsyncSessionLocal
    from app.modules.experiment_runs.repository import ExperimentRunRepository
    from app.modules.experiment_runs.service import ExperimentRunService

    async def _run() -> bool:
        async with AsyncSessionLocal() as session:
            service = ExperimentRunService(ExperimentRunRepository(session))
            return await service.apply_machine_completion(wip_id)

    loop = asyncio.new_event_loop()
    try:
        handled = loop.run_until_complete(_run())
    finally:
        loop.close()

    return {"wipId": wip_id, "handled": handled}

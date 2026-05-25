"""派工 / 排程商業邏輯。

Status values stored verbatim in Chinese: 待派工 / 排程中 / 待上機.

Strategies (different orderings of the pending dispatches when assigning a
suggested machine):
    FIFO              → creation / dispatchId order
    Priority First    → by priority (高 > 中 > 低), tie-break dispatchId
    Earliest Due Date → by dueAt ascending
    Least Setup Change→ group by experimentItem (so same-item runs stay adjacent)
    Hybrid            → priority then dueAt
"""

from __future__ import annotations

from collections.abc import Sequence

from app.common.errors import ConflictError, NotFoundError, ValidationError
from app.db.models import Dispatch, Machine
from app.modules.dispatches.repository import DispatchRepository
from app.modules.dispatches.schemas import (
    AssignDispatchPayload,
    CreateDispatchPayload,
)
from app.modules.dispatches.serializers import dispatch_dict

STATUS_PENDING = "待派工"
STATUS_SCHEDULING = "排程中"
STATUS_WAITING_LOAD = "待上機"

VALID_STRATEGIES = {
    "FIFO",
    "Priority First",
    "Earliest Due Date",
    "Least Setup Change",
    "Hybrid",
}

# 高/中/低 → sort weight (higher = more urgent)
_PRIORITY_RANK = {"高": 3, "中": 2, "低": 1}


def _priority_weight(value: str) -> int:
    return _PRIORITY_RANK.get(value, 0)


def _order_by_strategy(dispatches: list[Dispatch], strategy: str) -> list[Dispatch]:
    """Return the dispatches re-ordered per the chosen strategy.

    The ordering is the visible, coherent effect of each strategy; suggestion
    itself (matching a machine to the item) is the same for every strategy.
    """
    if strategy == "Priority First":
        return sorted(
            dispatches,
            key=lambda d: (-_priority_weight(d.priority), d.dispatch_id),
        )
    if strategy == "Earliest Due Date":
        return sorted(dispatches, key=lambda d: (d.due_at or "9999", d.dispatch_id))
    if strategy == "Least Setup Change":
        # group by experiment item so consecutive runs share setup
        return sorted(dispatches, key=lambda d: (d.experiment_item, d.dispatch_id))
    if strategy == "Hybrid":
        return sorted(
            dispatches,
            key=lambda d: (-_priority_weight(d.priority), d.due_at or "9999", d.dispatch_id),
        )
    # FIFO (default): creation / dispatchId order
    return sorted(dispatches, key=lambda d: d.dispatch_id)


def _match_machine(item: str, machines: Sequence[Machine]) -> str | None:
    """Pick a machine whose supportedItems includes the experiment item.

    Returns the machine_id, or None if nothing supports the item (does NOT
    crash — caller leaves suggestedMachineId null).
    """
    for m in machines:
        if item in (m.supported_items or []):
            return m.machine_id
    return None


class DispatchService:
    def __init__(self, repo: DispatchRepository) -> None:
        self._repo = repo

    async def list_dispatches(self) -> list[dict]:
        dispatches = await self._repo.list_dispatches()
        return [dispatch_dict(d) for d in dispatches]

    async def _require(self, dispatch_id: str) -> Dispatch:
        dispatch = await self._repo.get_by_dispatch_id(dispatch_id)
        if dispatch is None:
            raise NotFoundError(f"找不到派工單：{dispatch_id}")
        return dispatch

    @staticmethod
    def _validate_strategy(strategy: str) -> None:
        if strategy not in VALID_STRATEGIES:
            raise ValidationError(
                f"無效的排程策略：{strategy}（需為 {'/'.join(sorted(VALID_STRATEGIES))}）"
            )

    async def create(self, payload: CreateDispatchPayload, created_by: str) -> dict:
        if await self._repo.get_by_dispatch_id(payload.dispatch_id) is not None:
            raise ConflictError(f"派工單編號已存在：{payload.dispatch_id}")
        dispatch = Dispatch(
            dispatch_id=payload.dispatch_id,
            wip_id=payload.wip_id,
            order_id=payload.order_id,
            experiment_item=payload.experiment_item,
            priority=payload.priority,
            due_at=payload.due_at,
            status=STATUS_PENDING,
            created_by=created_by,
        )
        self._repo.add(dispatch)
        await self._repo.commit()
        return dispatch_dict(dispatch)

    async def suggest(self, strategy: str) -> list[dict]:
        """Run the chosen strategy over all 待派工 dispatches: set a suggested
        machine and move them to 排程中. Returns the affected dispatches."""
        self._validate_strategy(strategy)
        pending = list(await self._repo.list_by_statuses([STATUS_PENDING]))
        machines = await self._repo.list_machines()
        ordered = _order_by_strategy(pending, strategy)
        for d in ordered:
            d.suggested_machine_id = _match_machine(d.experiment_item, machines)
            d.status = STATUS_SCHEDULING
            d.strategy = strategy
        await self._repo.commit()
        return [dispatch_dict(d) for d in ordered]

    async def replan(self, reason: str, strategy: str) -> list[dict]:
        """Re-run suggestion for 排程中 (and 待派工) dispatches with a new
        strategy; record strategy + replanReason. Returns affected dispatches."""
        self._validate_strategy(strategy)
        affected = list(await self._repo.list_by_statuses([STATUS_PENDING, STATUS_SCHEDULING]))
        machines = await self._repo.list_machines()
        ordered = _order_by_strategy(affected, strategy)
        for d in ordered:
            d.suggested_machine_id = _match_machine(d.experiment_item, machines)
            d.status = STATUS_SCHEDULING
            d.strategy = strategy
            d.replan_reason = reason
        await self._repo.commit()
        return [dispatch_dict(d) for d in ordered]

    async def assign(
        self, dispatch_id: str, payload: AssignDispatchPayload, assigned_by: str
    ) -> dict:
        """指派機台 / Recipe（排程中 → 待上機）。"""
        dispatch = await self._require(dispatch_id)
        if dispatch.status != STATUS_SCHEDULING:
            raise ConflictError(f"派工單目前為「{dispatch.status}」，僅「排程中」可指派機台")

        machine = await self._repo.get_machine(payload.machine_id)
        if machine is None:
            raise NotFoundError(f"找不到機台：{payload.machine_id}")
        if dispatch.experiment_item not in (machine.supported_items or []):
            raise ValidationError(
                f"機台 {machine.machine_id} 不支援實驗項目「{dispatch.experiment_item}」"
            )

        recipe = await self._repo.get_recipe(payload.recipe_id)
        if recipe is None:
            raise NotFoundError(f"找不到 Recipe：{payload.recipe_id}")
        if recipe.experiment_item != dispatch.experiment_item:
            raise ValidationError(
                f"Recipe {recipe.recipe_id} 適用項目為「{recipe.experiment_item}」，"
                f"與派工項目「{dispatch.experiment_item}」不符"
            )
        if recipe.machine_ids and machine.machine_id not in recipe.machine_ids:
            raise ValidationError(f"Recipe {recipe.recipe_id} 不適用於機台 {machine.machine_id}")

        dispatch.assigned_machine_id = payload.machine_id
        dispatch.assigned_recipe_id = payload.recipe_id
        dispatch.scheduled_start = payload.scheduled_start
        dispatch.scheduled_end = payload.scheduled_end
        dispatch.assigned_by = assigned_by
        dispatch.status = STATUS_WAITING_LOAD
        await self._repo.commit()
        return dispatch_dict(dispatch)

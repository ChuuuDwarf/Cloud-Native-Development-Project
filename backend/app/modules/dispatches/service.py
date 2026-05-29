"""派工 / 排程商業邏輯。

Status values stored verbatim in Chinese: 待排程 / 待派工 / 待上機.

Strategies (different orderings of the pending dispatches when assigning a
suggested machine):
    FIFO              → creation / dispatchId order
    Priority First    → by priority (高 > 中 > 低), tie-break dispatchId
    Earliest Due Date → by dueAt ascending
    Least Setup Change→ group by experimentItem (so same-item runs stay adjacent)
    Hybrid            → priority then dueAt
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import datetime

from app.common.dependencies.lab_scope import LabScope
from app.common.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.db.models import Dispatch, Machine, WipHistory
from app.modules.dashboard.publisher import publish_dashboard_event
from app.modules.dispatches.repository import DispatchRepository
from app.modules.dispatches.schemas import (
    AssignDispatchPayload,
    CreateDispatchPayload,
)
from app.modules.dispatches.serializers import dispatch_dict

logger = logging.getLogger(__name__)

STATUS_PENDING = "待排程"
STATUS_SCHEDULING = "待派工"
STATUS_WAITING_LOAD = "待上機"

# B's coarse wips.status — the 派工排程 chain, in forward order. C drives the WIP
# along this as the dispatch progresses (建立→待排程 / 排程→待派工 / 指派→待上機),
# so 派工排程 is reflected on the WIP without touching A/B code. A WIP that is
# already running/ended sits outside the chain and is never regressed.
# See flow.md WIP 狀態機 and [[cd-flow-chain-enforced]].
WIP_DISPATCHED = "dispatched"
_WIP_CHAIN = ["created", "waiting_schedule", "scheduled", "dispatched"]

VALID_STRATEGIES = {
    "FIFO",
    "Priority First",
    "Earliest Due Date",
    "Least Setup Change",
    "Hybrid",
}

# 高/中/低 → sort weight (higher = more urgent)
_PRIORITY_RANK = {"高": 3, "中": 2, "低": 1}


def _now() -> datetime:
    return datetime.now()


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
    def __init__(self, repo: DispatchRepository, scope: LabScope) -> None:
        self._repo = repo
        self._scope = scope

    async def list_dispatches(self) -> list[dict]:
        if self._scope.restricted_without_lab:
            return []
        dispatches = await self._repo.list_dispatches(lab_code=self._scope.list_lab_code_filter())
        return [dispatch_dict(d) for d in dispatches]

    @staticmethod
    async def _publish_dispatch_change(lab_code: str | None, event_name: str) -> None:
        """Best-effort dashboard SSE fanout. ``dispatch.lab`` is already a
        lab CODE (ASCII), matching what the SSE handler subscribes off, so no
        Lab.name -> Lab.code translation is needed here. Errors are
        swallowed — the dispatch action itself is already committed.
        """
        try:
            await publish_dashboard_event(lab_code or None, event_name)
        except Exception:
            logger.exception("dashboard publish %s failed lab=%s", event_name, lab_code)

    async def _require(self, dispatch_id: str) -> Dispatch:
        dispatch = await self._repo.get_by_dispatch_id(dispatch_id)
        if dispatch is None:
            raise NotFoundError(f"找不到派工單：{dispatch_id}")
        # Hide cross-lab dispatches as 404 (don't leak existence).
        if not self._scope.sees_all_labs and dispatch.lab != self._scope.lab_code:
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

        # Derive dispatch.lab from the WIP it's tied to, so future list-scope
        # filters can find it. WIP stores display name (Chinese), dispatches
        # stores short code; resolve via labs table.
        wip = await self._repo.get_wip_by_no(payload.wip_id)
        if wip is None:
            raise NotFoundError(f"找不到 WIP：{payload.wip_id}")
        dispatch_lab = ""
        if wip.lab_name:
            dispatch_lab = (await self._repo.lab_code_for_name(wip.lab_name)) or ""
        # Reject if caller can't access this WIP's lab.
        if not self._scope.can_access_lab(dispatch_lab):
            raise ForbiddenError(f"無權限為實驗室 {dispatch_lab} 建立派工單")

        dispatch = Dispatch(
            dispatch_id=payload.dispatch_id,
            wip_id=payload.wip_id,
            order_id=payload.order_id,
            experiment_item=payload.experiment_item,
            priority=payload.priority,
            due_at=payload.due_at,
            status=STATUS_PENDING,
            created_by=created_by,
            lab=dispatch_lab,
        )
        self._repo.add(dispatch)
        # 建立派工單 → WIP 進入待排程（送排程）。
        await self._sync_wip_status(
            payload.wip_id,
            "waiting_schedule",
            "送入待排程",
            f"派工單 {payload.dispatch_id} 建立，WIP 送入待排程",
            created_by,
        )
        await self._repo.commit()
        await self._publish_dispatch_change(dispatch.lab, "dispatch_created")
        return dispatch_dict(dispatch)

    async def suggest(self, strategy: str) -> list[dict]:
        """Run the chosen strategy over all 待排程 dispatches: set a suggested
        machine and move them to 待派工. Returns the affected dispatches."""
        self._validate_strategy(strategy)
        if self._scope.restricted_without_lab:
            return []
        lab_filter = self._scope.list_lab_code_filter()
        pending = list(await self._repo.list_by_statuses([STATUS_PENDING], lab_code=lab_filter))
        machines = await self._repo.list_machines(lab_code=lab_filter)
        ordered = _order_by_strategy(pending, strategy)
        for d in ordered:
            d.suggested_machine_id = _match_machine(d.experiment_item, machines)
            d.status = STATUS_SCHEDULING
            d.strategy = strategy
            # 排程建議 → WIP 進入待派工。
            await self._sync_wip_status(
                d.wip_id,
                "scheduled",
                "排程",
                f"派工單 {d.dispatch_id} 進入待派工（策略：{strategy}）",
                "系統(排程)",
            )
        await self._repo.commit()
        # Publish once per distinct lab touched (multiple dispatches may
        # share a lab; cross-lab callers can affect several labs at once).
        # Skip the publish entirely when nothing moved — no UI to refresh.
        for code in {d.lab for d in ordered if d.lab}:
            await self._publish_dispatch_change(code, "dispatch_suggested")
        return [dispatch_dict(d) for d in ordered]

    async def replan(self, reason: str, strategy: str) -> list[dict]:
        """Re-run suggestion for 待派工 (and 待排程) dispatches with a new
        strategy; record strategy + replanReason. Returns affected dispatches."""
        self._validate_strategy(strategy)
        if self._scope.restricted_without_lab:
            return []
        lab_filter = self._scope.list_lab_code_filter()
        affected = list(
            await self._repo.list_by_statuses(
                [STATUS_PENDING, STATUS_SCHEDULING], lab_code=lab_filter
            )
        )
        machines = await self._repo.list_machines(lab_code=lab_filter)
        ordered = _order_by_strategy(affected, strategy)
        for d in ordered:
            d.suggested_machine_id = _match_machine(d.experiment_item, machines)
            d.status = STATUS_SCHEDULING
            d.strategy = strategy
            d.replan_reason = reason
            # 重新排程 → WIP 進入待派工。
            await self._sync_wip_status(
                d.wip_id,
                "scheduled",
                "重新排程",
                f"派工單 {d.dispatch_id} 重新排程（策略：{strategy}）",
                "系統(排程)",
            )
        await self._repo.commit()
        for code in {d.lab for d in ordered if d.lab}:
            await self._publish_dispatch_change(code, "dispatch_replanned")
        return [dispatch_dict(d) for d in ordered]

    async def assign(
        self, dispatch_id: str, payload: AssignDispatchPayload, assigned_by: str
    ) -> dict:
        """指派機台 / Recipe（待派工 → 待上機）。"""
        dispatch = await self._require(dispatch_id)
        if dispatch.status != STATUS_SCHEDULING:
            raise ConflictError(f"派工單目前為「{dispatch.status}」，僅「待派工」可指派機台")

        machine = await self._repo.get_machine(payload.machine_id)
        if machine is None:
            raise NotFoundError(f"找不到機台：{payload.machine_id}")
        # Block assigning a machine from another lab (same 404 as not-found
        # so existence isn't leaked).
        if not self._scope.can_access_lab(machine.lab):
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

        # C→B handoff: 指派完成 → WIP 進入待上機（待上機是 D 上機的前置條件）。
        await self._sync_wip_status(
            dispatch.wip_id,
            WIP_DISPATCHED,
            "派工指派",
            (
                f"派工單 {dispatch.dispatch_id} 指派機台 {dispatch.assigned_machine_id}"
                f" / Recipe {dispatch.assigned_recipe_id}，WIP 進入待上機"
            ),
            assigned_by,
            strict=True,
        )

        await self._repo.commit()
        await self._publish_dispatch_change(dispatch.lab, "dispatch_assigned")
        return dispatch_dict(dispatch)

    async def _sync_wip_status(
        self,
        wip_no: str,
        target: str,
        action: str,
        description: str,
        actor: str,
        *,
        strict: bool = False,
    ) -> None:
        """Advance the dispatch's WIP (B's ``wips``) forward along the 派工排程 chain.

        Drives B's ``wips.status`` from C so 建立派工 / 排程 / 指派 are reflected on
        the WIP — without touching A/B code. Forward-only: never regresses nor
        re-writes history if the WIP is already at/ahead of ``target``. A WIP that
        is running/ended sits outside the chain and is left alone (``strict`` →
        ``ConflictError``). ``dispatches.wip_id`` == ``wips.wip_no``.
        See [[cd-flow-chain-enforced]].
        """
        wip = await self._repo.get_wip_by_no(wip_no)
        if wip is None:
            logger.warning("Dispatch WIP %r not found; skip %s", wip_no, action)
            return
        if wip.status not in _WIP_CHAIN:
            if strict:
                raise ConflictError(
                    f"WIP {wip.wip_no} 目前為「{wip.status}」，已在執行或結束，無法{action}"
                )
            logger.warning(
                "WIP %s status %r outside 派工排程 chain; skip %s", wip.wip_no, wip.status, action
            )
            return
        if _WIP_CHAIN.index(target) <= _WIP_CHAIN.index(wip.status):
            return  # already at/ahead of target — don't regress or duplicate history
        from_status = wip.status
        wip.status = target
        if target == WIP_DISPATCHED:
            wip.dispatched_at = _now()
        self._repo.add_wip_history(
            WipHistory(
                wip_id=wip.id,
                action=action,
                from_status=from_status,
                to_status=target,
                description=description,
                operator_name=actor,
            )
        )

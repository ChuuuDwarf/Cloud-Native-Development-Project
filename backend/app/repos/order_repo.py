from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import datetime
from typing import Any, Protocol
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import String, cast, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.common.dependencies import CurrentUser
from app.core.order_constants import EDITABLE_STATUSES, FINAL_STATUSES, TRANSITIONS
from app.core.order_enums import OrderAction, OrderStatus, PriorityLevel
from app.core.order_errors import bad_request, not_found
from app.core.order_security import require_role, user_id
from app.core.time import generate_order_no, utc_now
from app.db.models import Department, Lab, LabCapability
from app.db.models.order_management import (
    OrderHistoryModel,
    OrderItemModel,
    OrderModel,
    QuotaSettingModel,
    QuotaUsageModel,
)
from app.modules.dashboard.publisher import (
    publish_dashboard_event,
    publish_new_pending_approval,
)
from app.repos.order_mappers import history_to_schema, order_to_schema
from app.schemas.order import (
    Order,
    OrderActionRequest,
    OrderCreate,
    OrderHistory,
    OrderItemCreate,
    OrderUpdate,
    QuotaPatchPayload,
    QuotaPayload,
)

logger = logging.getLogger(__name__)


class OrderItemMasterData(Protocol):
    sample_id: str
    sample_name: str | None
    lab_id: str
    experiment_id: str


class OrderRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_order(self, payload: OrderCreate, current_user: CurrentUser) -> Order:
        require_role(current_user, {"plant_user"})
        await self._validate_order_master_data(payload.department_id, payload.items)

        applicant_id = user_id(current_user)
        now = utc_now()
        order = OrderModel(
            order_no=f"PENDING-{uuid4().hex}",
            applicant_id=applicant_id,
            department_id=payload.department_id,
            apply_date=payload.apply_date or now,
            status=OrderStatus.DRAFT.value,
            priority=(payload.priority or PriorityLevel.NORMAL).value,
            total_items=len(payload.items),
            created_at=now,
            updated_at=now,
        )
        order.items = [self._make_item(item, now) for item in payload.items]
        self.db.add(order)
        await self.db.flush()

        order.order_no = generate_order_no(order.id)
        self._append_history(
            order=order,
            actor_id=applicant_id,
            action="create",
            from_status=None,
            to_status=OrderStatus.DRAFT.value,
        )
        await self.db.commit()
        return await self.get_order(order.id)

    async def list_orders(
        self,
        status_filter: OrderStatus | None = None,
        applicant_id: str | None = None,
        current_user: CurrentUser | None = None,
    ) -> list[Order]:
        stmt = (
            select(OrderModel)
            .options(joinedload(OrderModel.items))
            .where(OrderModel.is_deleted.is_(False))
            .order_by(OrderModel.created_at.desc())
        )

        if status_filter is not None:
            stmt = stmt.where(OrderModel.status == status_filter.value)

        if applicant_id:
            stmt = stmt.where(OrderModel.applicant_id == applicant_id)

        # 審核頁:主管只看得到自己 Lab 底下還能審的委託單
        if (
            current_user is not None
            and status_filter == OrderStatus.PENDING_APPROVAL
            and not applicant_id
        ):
            actor = require_role(current_user, {"lab_supervisor"})
            lab_ids = set(actor.get("labIds", []))
            all_labs = bool(actor.get("allLabs"))

            # Cross-lab roles (system_admin, general_supervisor) approve
            # everywhere — no lab filter. Lab-bound roles with no lab fall
            # through to the empty-list response (misconfigured account).
            if not lab_ids and not all_labs:
                return []

            approvable_item_filters = [
                OrderItemModel.order_id == OrderModel.id,
                OrderItemModel.status.in_(
                    [
                        OrderStatus.PENDING_APPROVAL.value,
                        OrderStatus.DRAFT.value,
                    ]
                ),
            ]
            if not all_labs:
                approvable_item_filters.append(OrderItemModel.lab_id.in_(lab_ids))

            approvable_item_exists = (
                select(OrderItemModel.id).where(*approvable_item_filters).exists()
            )

            stmt = stmt.where(approvable_item_exists)

        orders = (await self.db.execute(stmt)).unique().scalars().all()
        return [order_to_schema(order) for order in orders]

    async def get_order(self, order_id: int) -> Order:
        return order_to_schema(await self._get_order_model(order_id))

    async def update_order(
        self, order_id: int, payload: OrderUpdate, current_user: CurrentUser
    ) -> Order:
        now = utc_now()
        order = await self._get_order_model(order_id)
        actor_id = user_id(current_user)
        require_role(current_user, {"plant_user"})
        if actor_id != order.applicant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the applicant can update this order",
            )

        if OrderStatus(order.status) not in EDITABLE_STATUSES:
            raise bad_request("Only draft or returned orders can be edited")

        next_department_id = (
            payload.department_id if payload.department_id is not None else order.department_id
        )

        next_items: Sequence[OrderItemMasterData]
        if payload.items is not None:
            next_items = payload.items
        else:
            next_items = [
                OrderItemCreate(
                    sampleId=item.sample_id,
                    sampleName=item.sample_name,
                    labId=item.lab_id,
                    experimentId=item.experiment_id,
                )
                for item in order.items
            ]

        await self._validate_order_master_data(next_department_id, next_items)

        if payload.department_id is not None:
            order.department_id = payload.department_id
        if payload.apply_date is not None:
            order.apply_date = payload.apply_date
        if payload.priority is not None:
            order.priority = payload.priority.value
        if payload.items is not None:
            # Support partial item updates: if an item includes orderItemId, update that existing
            # returned order item only (reset status to draft and clear reasons). Otherwise
            # replace full item list (existing behavior).
            if any(getattr(item, "order_item_id", None) for item in payload.items):
                for item_patch in payload.items:
                    if item_patch.order_item_id is None:
                        continue
                    # find matching item
                    target = next(
                        (it for it in order.items if it.id == item_patch.order_item_id),
                        None,
                    )
                    if target is None:
                        raise not_found("Order item not found")
                    # only allow editing returned items
                    if target.status != OrderStatus.RETURNED.value:
                        raise bad_request("Only returned order items can be edited individually")

                    # validate mapping for new lab/experiment
                    await self._validate_order_master_data(
                        order.department_id,
                        [
                            OrderItemCreate(
                                sampleId=item_patch.sample_id,
                                sampleName=item_patch.sample_name,
                                labId=item_patch.lab_id,
                                experimentId=item_patch.experiment_id,
                            )
                        ],
                    )

                    target.sample_id = item_patch.sample_id
                    target.sample_name = item_patch.sample_name
                    target.lab_id = item_patch.lab_id
                    target.experiment_id = item_patch.experiment_id
                    target.status = OrderStatus.DRAFT.value
                    target.return_reason = None
                    target.reject_reason = None
                    target.approved_by = None
                    target.approved_at = None
                    target.quota_override = False
                    target.quota_override_reason = None
                    target.quota_approved_by = None
                    target.quota_approved_at = None
                    target.updated_at = now
                order.total_items = len(order.items)
            else:
                order.items.clear()
                await self.db.flush()
                order.items = [self._make_item(item, now) for item in payload.items]
                order.total_items = len(order.items)

        order.updated_at = now
        self._append_history(
            order=order,
            actor_id=actor_id,
            action="update",
            from_status=order.status,
            to_status=order.status,
        )
        await self.db.commit()
        return await self.get_order(order.id)

    async def delete_order(self, order_id: int, current_user: CurrentUser) -> None:
        now = utc_now()
        order = await self._get_order_model(order_id)
        actor_id = user_id(current_user)
        require_role(current_user, {"plant_user"})
        if actor_id != order.applicant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the applicant can delete this order",
            )
        if order.status != OrderStatus.DRAFT.value:
            raise bad_request("Only draft orders can be deleted")

        order.is_deleted = True
        order.updated_at = now
        self._append_history(
            order=order,
            actor_id=actor_id,
            action="delete",
            from_status=order.status,
            to_status=order.status,
        )
        await self.db.commit()

    async def apply_action(
        self,
        order_id: int,
        payload: OrderActionRequest,
        current_user: CurrentUser,
    ) -> Order:
        now = utc_now()
        order = await self._get_order_model(order_id)
        current_status = OrderStatus(order.status)
        actor_id = user_id(current_user)

        if current_status in FINAL_STATUSES:
            raise bad_request(f"Order is already {current_status.value} and cannot be changed")

        allowed_statuses, to_status, _message = TRANSITIONS[payload.action]
        if current_status not in allowed_statuses:
            raise bad_request(f"Cannot run {payload.action.value} from {current_status.value}")

        from_status = order.status

        if payload.action in {OrderAction.SUBMIT, OrderAction.CANCEL}:
            require_role(current_user, {"plant_user"})
            if actor_id != order.applicant_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only the applicant can submit or cancel this order",
                )

        elif payload.action in {OrderAction.APPROVE, OrderAction.RETURN, OrderAction.REJECT}:
            actor = require_role(current_user, {"lab_supervisor"})
            lab_ids = set(actor.get("labIds", []))
            all_labs = bool(actor.get("allLabs"))
            target_items = [
                item
                for item in order.items
                # Lab gate: cross-lab roles bypass; lab-bound roles only act
                # on items in their own lab.
                if (all_labs or item.lab_id in lab_ids)
                and (payload.order_item_id is None or item.id == payload.order_item_id)
                and (
                    item.status == OrderStatus.PENDING_APPROVAL.value
                    or (
                        order.status == OrderStatus.PENDING_APPROVAL.value
                        and item.status == OrderStatus.DRAFT.value
                    )
                )
            ]

            if not target_items:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No approvable order items for this manager",
                )

            for item in target_items:
                if item.status == OrderStatus.DRAFT.value:
                    item.status = OrderStatus.PENDING_APPROVAL.value

            if payload.action == OrderAction.APPROVE:
                exceeded_items = [
                    item for item in target_items if item.quota_exceeded and not item.quota_override
                ]
                if exceeded_items and not payload.quota_override:
                    raise bad_request(
                        "One or more order items exceed quota. "
                        "Approve those items with quotaOverride and reason."
                    )

                for item in target_items:
                    item.status = OrderStatus.APPROVED.value
                    item.approved_by = actor_id
                    item.approved_at = now
                    item.return_reason = None
                    item.reject_reason = None
                    if payload.quota_override:
                        item.quota_exceeded = True
                        item.quota_override = True
                        item.quota_override_reason = payload.reason
                        item.quota_approved_by = actor_id
                        item.quota_approved_at = now
                    item.updated_at = now

                order.status = self.aggregate_approval_status(order)
                if order.status == OrderStatus.APPROVED.value:
                    await self.record_quota_usage(order)

            elif payload.action == OrderAction.RETURN:
                for item in target_items:
                    item.status = OrderStatus.RETURNED.value
                    item.return_reason = payload.reason
                    item.updated_at = now
                order.status = self.aggregate_approval_status(order)

            elif payload.action == OrderAction.REJECT:
                # If a manager rejects an item, the business rule is to reject the whole order.
                # Keep the existing authorization check
                # (target_items must be non-empty for this manager).
                for item in order.items:
                    item.status = OrderStatus.REJECTED.value
                    item.reject_reason = payload.reason
                    item.updated_at = now
                order.status = OrderStatus.REJECTED.value

        else:
            if payload.action == OrderAction.CONFIRM_DELIVERY:
                require_role(current_user, {"plant_user"})
                if actor_id != order.applicant_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Only the applicant can confirm sample delivery",
                    )

                await self.create_samples_for_confirmed_delivery(order, current_user)
            else:
                require_role(current_user, {"lab_engineer", "lab_supervisor"})
            order.status = to_status.value

        if payload.action == OrderAction.SUBMIT:
            remaining_quota = await self.effective_remaining_quota(order)
            for index, item in enumerate(order.items):
                item.status = OrderStatus.PENDING_APPROVAL.value
                item.approved_by = None
                item.approved_at = None
                item.return_reason = None
                item.reject_reason = None
                item.quota_override = False
                item.quota_override_reason = None
                item.quota_approved_by = None
                item.quota_approved_at = None
                item.quota_exceeded = index >= remaining_quota
                item.updated_at = now

            quota_check = await self.check_quota_for_order(order)
            if quota_check["needOverride"]:
                order.last_reason = "配額超額,需主管特批"
            else:
                order.last_reason = None
            order.status = OrderStatus.PENDING_APPROVAL.value

        elif payload.action == OrderAction.CANCEL:
            order.status = OrderStatus.CANCELLED.value
            order.last_reason = payload.reason

        elif payload.reason is not None:
            order.last_reason = payload.reason

        order.updated_at = now
        self._append_history(
            order=order,
            actor_id=actor_id,
            action=payload.action.value,
            from_status=from_status,
            to_status=order.status,
            reason=payload.reason,
            quota_override=payload.quota_override,
        )
        await self.db.commit()

        # Best-effort dashboard SSE fanout for a fresh PENDING_APPROVAL.
        # Order items may span multiple labs (or be lab-less if items are
        # not yet attached), so this is a global event. Publisher swallows
        # Redis errors; we belt-and-suspenders the call too.
        if payload.action == OrderAction.SUBMIT:
            await publish_new_pending_approval(None)
        elif payload.action in {
            OrderAction.APPROVE,
            OrderAction.RETURN,
            OrderAction.REJECT,
            OrderAction.CANCEL,
        }:
            # 待簽 KPI on the lab_supervisor dashboard moves on these terminal
            # actions; publish per touched lab so each supervisor's view
            # invalidates. Cross-lab viewers also pick this up via the
            # ``dashboard:events:*`` psubscribe.
            try:
                lab_code_rows = await self.db.execute(
                    select(OrderItemModel.lab_id)
                    .where(OrderItemModel.order_id == order.id)
                    .distinct()
                )
                lab_codes = [code for code in lab_code_rows.scalars() if code]
                event_name = f"order_{payload.action.value.lower()}"
                if lab_codes:
                    for code in lab_codes:
                        await publish_dashboard_event(code, event_name)
                else:
                    # No items attached yet — broadcast global so cross-lab
                    # viewers still refresh.
                    await publish_dashboard_event(None, event_name)
            except Exception:
                # Best-effort: a publish failure must not unwind the action.
                logger.exception(
                    "dashboard publish for order action %s failed order=%s",
                    payload.action.value,
                    order.id,
                )

        return await self.get_order(order.id)

    async def get_history(self, order_id: int) -> list[OrderHistory]:
        order = await self._get_order_model(order_id)
        stmt = (
            select(OrderHistoryModel)
            .where(OrderHistoryModel.order_id == order.id)
            .order_by(OrderHistoryModel.action_time.asc(), OrderHistoryModel.id.asc())
        )
        histories = (await self.db.execute(stmt)).scalars().all()
        return [history_to_schema(history) for history in histories]

    async def list_quota_settings(self) -> list[QuotaSettingModel]:
        stmt = select(QuotaSettingModel).order_by(QuotaSettingModel.id.asc())
        return list((await self.db.execute(stmt)).scalars().all())

    async def create_quota_setting(self, payload: QuotaPayload) -> QuotaSettingModel:
        now = utc_now()
        quota = QuotaSettingModel(
            scope_type=payload.scope_type,
            scope_id=payload.scope_id,
            monthly_limit=payload.monthly_limit,
            urgent_limit=payload.urgent_limit,
            critical_limit=payload.critical_limit,
            is_active=payload.is_active,
            created_at=now,
            updated_at=now,
        )
        self.db.add(quota)
        await self.db.commit()
        await self.db.refresh(quota)
        return quota

    async def update_quota_setting(
        self, quota_id: int, payload: QuotaPatchPayload
    ) -> QuotaSettingModel:
        quota = await self.db.get(QuotaSettingModel, quota_id)
        if quota is None:
            raise not_found("Quota setting not found")
        if payload.monthly_limit is not None:
            quota.monthly_limit = payload.monthly_limit
        if payload.urgent_limit is not None:
            quota.urgent_limit = payload.urgent_limit
        if payload.critical_limit is not None:
            quota.critical_limit = payload.critical_limit
        if payload.is_active is not None:
            quota.is_active = payload.is_active
        quota.updated_at = utc_now()
        await self.db.commit()
        await self.db.refresh(quota)
        return quota

    async def check_quota_for_order(self, order: OrderModel) -> dict[str, Any]:
        checks: list[dict[str, Any]] = [
            item
            for item in (
                await self._quota_check(
                    "user", order.applicant_id, order.total_items, order.priority
                ),
                await self._quota_check(
                    "department", order.department_id, order.total_items, order.priority
                ),
            )
            if item is not None
        ]
        allowed = all(item["allowed"] for item in checks) if checks else True
        return {"allowed": allowed, "needOverride": not allowed, "checks": checks}

    async def check_quota(
        self,
        applicant_id: str,
        department_id: str,
        item_count: int,
        priority: str = "normal",
    ) -> dict[str, Any]:
        checks: list[dict[str, Any]] = [
            item
            for item in (
                await self._quota_check("user", applicant_id, item_count, priority),
                await self._quota_check("department", department_id, item_count, priority),
            )
            if item is not None
        ]
        allowed = all(item["allowed"] for item in checks) if checks else True
        return {"allowed": allowed, "needOverride": not allowed, "checks": checks}

    async def effective_remaining_quota(self, order: OrderModel) -> int:
        remaining_values: list[int] = [
            value
            for value in (
                await self._quota_remaining("user", order.applicant_id, order.priority),
                await self._quota_remaining("department", order.department_id, order.priority),
            )
            if value is not None
        ]
        if not remaining_values:
            return order.total_items
        return max(min(remaining_values), 0)

    def aggregate_approval_status(self, order: OrderModel) -> str:
        # Prioritize rejected and returned states over pending/draft so that a single
        # returned or rejected item updates the main order status accordingly.
        item_statuses = {item.status for item in order.items}
        if OrderStatus.REJECTED.value in item_statuses:
            return OrderStatus.REJECTED.value
        if OrderStatus.RETURNED.value in item_statuses:
            return OrderStatus.RETURNED.value
        if item_statuses == {OrderStatus.APPROVED.value}:
            return OrderStatus.APPROVED.value
        if (
            OrderStatus.PENDING_APPROVAL.value in item_statuses
            or OrderStatus.DRAFT.value in item_statuses
        ):
            return OrderStatus.PENDING_APPROVAL.value
        return order.status

    async def record_quota_usage(self, order: OrderModel) -> None:
        existing_usage = (
            await self.db.execute(
                select(QuotaUsageModel).where(QuotaUsageModel.order_id == order.id)
            )
        ).scalar_one_or_none()
        if existing_usage:
            return
        now = utc_now()
        for scope_type, scope_id in (
            ("user", order.applicant_id),
            ("department", order.department_id),
        ):
            self.db.add(
                QuotaUsageModel(
                    scope_type=scope_type,
                    scope_id=scope_id,
                    year=now.year,
                    month=now.month,
                    used_count=order.total_items,
                    urgent_used_count=(
                        order.total_items if order.priority == PriorityLevel.URGENT.value else 0
                    ),
                    critical_used_count=(
                        order.total_items if order.priority == PriorityLevel.CRITICAL.value else 0
                    ),
                    order_id=order.id,
                    created_at=now,
                    updated_at=now,
                )
            )

    async def create_samples_for_confirmed_delivery(
        self,
        order: OrderModel,
        current_user: CurrentUser,
    ) -> None:
        """Create pending samples when the applicant confirms delivery.

        Business rule:
        - One physical sample should only create one row in `samples`.
        - Multiple approved order items with the same `sample_id` are merged into the
          same sample row.
        - The merged `experiment_item` keeps lab/experiment information so the sample
          module can split/dispatch the sample into WIPs later.
        """

        approved_items = [item for item in order.items if item.status == OrderStatus.APPROVED.value]
        if not approved_items:
            return

        lab_keys = {item.lab_id for item in approved_items if item.lab_id}
        experiment_keys = {item.experiment_id for item in approved_items if item.experiment_id}

        labs = (
            (
                await self.db.execute(
                    select(Lab).where(
                        (cast(Lab.id, String).in_(lab_keys)) | (Lab.code.in_(lab_keys))
                    )
                )
            )
            .scalars()
            .all()
        )
        labs_by_key: dict[str, Lab] = {str(lab.id): lab for lab in labs}
        labs_by_key.update({lab.code: lab for lab in labs})

        capabilities = (
            (
                await self.db.execute(
                    select(LabCapability).where(cast(LabCapability.id, String).in_(experiment_keys))
                )
            )
            .scalars()
            .all()
        )
        capabilities_by_id: dict[str, LabCapability] = {
            str(capability.id): capability for capability in capabilities
        }

        items_by_sample_no: dict[str, list[OrderItemModel]] = {}
        for item in approved_items:
            items_by_sample_no.setdefault(item.sample_id, []).append(item)

        for sample_no, sample_items in items_by_sample_no.items():
            # `samples.sample_no` is unique. This makes confirm_delivery idempotent:
            # if the button/API is triggered again, do not create duplicates.
            existing_sample = (
                await self.db.execute(
                    text(
                        """
                        SELECT id
                        FROM samples
                        WHERE sample_no = :sample_no
                        LIMIT 1
                        """
                    ),
                    {"sample_no": sample_no},
                )
            ).fetchone()
            if existing_sample is not None:
                continue

            experiment_parts: list[str] = []
            first_lab_name: str | None = None

            for item in sample_items:
                lab = labs_by_key.get(item.lab_id)
                capability = capabilities_by_id.get(item.experiment_id)

                lab_name = lab.name if lab is not None else item.lab_id
                experiment_name = (
                    capability.experiment_item if capability is not None else item.experiment_id
                )

                if first_lab_name is None:
                    first_lab_name = lab_name

                part = f"{lab_name}:{experiment_name}"
                if part not in experiment_parts:
                    experiment_parts.append(part)

            experiment_summary = self._truncate_text("、".join(experiment_parts), 100)
            current_location = f"{first_lab_name} 收樣區" if first_lab_name else "收樣區"

            sample_name_value = self._truncate_text(
                next(
                    (
                        item.sample_name
                        for item in sample_items
                        if item.sample_name and item.sample_name.strip()
                    ),
                    None,
                )
                or sample_no,
                100,
            )

            sample_result = await self.db.execute(
                text(
                    """
                    INSERT INTO samples (
                        sample_no,
                        order_no,
                        sample_name,
                        experiment_item,
                        applicant_name,
                        applicant_department,
                        status,
                        current_location,
                        note
                    )
                    VALUES (
                        :sample_no,
                        :order_no,
                        :sample_name,
                        :experiment_item,
                        :applicant_name,
                        :applicant_department,
                        'pending_receive',
                        :current_location,
                        :note
                    )
                    RETURNING id
                    """
                ),
                {
                    "sample_no": sample_no,
                    "order_no": order.order_no,
                    "sample_name": sample_name_value,
                    "experiment_item": experiment_summary,
                    "applicant_name": current_user.name,
                    "applicant_department": order.department_id,
                    "current_location": current_location,
                    "note": self._truncate_text(
                        f"由委託單 {order.order_no} 確認送樣自動建立",
                        500,
                    ),
                },
            )
            created_sample = sample_result.fetchone()
            if created_sample is None:
                continue

            sample_id = created_sample._mapping["id"]

            await self.db.execute(
                text(
                    """
                    INSERT INTO sample_histories (
                        sample_id,
                        action,
                        from_status,
                        to_status,
                        description,
                        operator_name,
                        lab_name
                    )
                    VALUES (
                        :sample_id,
                        'delivery_confirmed_create_sample',
                        NULL,
                        'pending_receive',
                        :description,
                        :operator_name,
                        :lab_name
                    )
                    """
                ),
                {
                    "sample_id": sample_id,
                    "description": (
                        f"確認送樣，待收樣品 {sample_no}，"
                        f"目前位置：{first_lab_name or current_location}"
                    ),
                    "operator_name": current_user.name,
                    "lab_name": first_lab_name,
                },
            )

    async def _quota_check(
        self,
        scope_type: str,
        scope_id: str,
        item_count: int,
        priority: str,
    ) -> dict[str, Any] | None:
        quota = (
            (
                await self.db.execute(
                    select(QuotaSettingModel)
                    .where(
                        QuotaSettingModel.scope_type == scope_type,
                        QuotaSettingModel.scope_id == scope_id,
                        QuotaSettingModel.is_active.is_(True),
                    )
                    .order_by(QuotaSettingModel.updated_at.desc(), QuotaSettingModel.id.desc())
                )
            )
            .scalars()
            .first()
        )

        if quota is None:
            return None

        now = utc_now()

        usages = (
            (
                await self.db.execute(
                    select(QuotaUsageModel).where(
                        QuotaUsageModel.scope_type == scope_type,
                        QuotaUsageModel.scope_id == scope_id,
                        QuotaUsageModel.year == now.year,
                        QuotaUsageModel.month == now.month,
                    )
                )
            )
            .scalars()
            .all()
        )

        used = sum(item.used_count for item in usages)
        urgent_used = sum(item.urgent_used_count for item in usages)
        critical_used = sum(item.critical_used_count for item in usages)

        reserved = await self._reserved_quota_count(scope_type, scope_id)

        urgent_requested = item_count if priority == PriorityLevel.URGENT.value else 0
        critical_requested = item_count if priority == PriorityLevel.CRITICAL.value else 0

        monthly_consumed = used + reserved
        monthly_after_request = monthly_consumed + item_count

        monthly_allowed = monthly_after_request <= quota.monthly_limit
        urgent_allowed = (
            quota.urgent_limit is None or urgent_used + urgent_requested <= quota.urgent_limit
        )
        critical_allowed = (
            quota.critical_limit is None
            or critical_used + critical_requested <= quota.critical_limit
        )

        allowed = monthly_allowed and urgent_allowed and critical_allowed

        return {
            "scopeType": scope_type,
            "scopeId": scope_id,
            "used": used,
            "reserved": reserved,
            "effectiveUsed": monthly_consumed,
            "limit": quota.monthly_limit,
            "urgentUsed": urgent_used,
            "urgentLimit": quota.urgent_limit,
            "criticalUsed": critical_used,
            "criticalLimit": quota.critical_limit,
            "requested": item_count,
            "remaining": max(quota.monthly_limit - monthly_consumed, 0),
            "allowed": allowed,
            "needOverride": not allowed,
        }

    async def _reserved_quota_count(self, scope_type: str, scope_id: str) -> int:
        if not scope_id or scope_id == "__not_applicable__":
            return 0

        conditions = [
            OrderModel.is_deleted.is_(False),
            OrderModel.status == OrderStatus.PENDING_APPROVAL.value,
        ]

        if scope_type == "user":
            conditions.append(OrderModel.applicant_id == scope_id)
        elif scope_type == "department":
            conditions.append(OrderModel.department_id == scope_id)
        else:
            return 0

        pending_orders = (
            (await self.db.execute(select(OrderModel).where(*conditions))).scalars().all()
        )

        return sum(order.total_items for order in pending_orders)

    async def _quota_remaining(self, scope_type: str, scope_id: str, priority: str) -> int | None:
        check = await self._quota_check(scope_type, scope_id, 0, priority)
        if check is None:
            return None

        remaining_values = [check["limit"] - check["effectiveUsed"]]

        if priority == PriorityLevel.URGENT.value and check["urgentLimit"] is not None:
            remaining_values.append(check["urgentLimit"] - check["urgentUsed"])

        if priority == PriorityLevel.CRITICAL.value and check["criticalLimit"] is not None:
            remaining_values.append(check["criticalLimit"] - check["criticalUsed"])

        return min(remaining_values)

    async def _get_order_model(self, order_id: int) -> OrderModel:
        stmt = (
            select(OrderModel)
            .options(joinedload(OrderModel.items))
            .where(OrderModel.id == order_id, OrderModel.is_deleted.is_(False))
        )
        order = (await self.db.execute(stmt)).unique().scalar_one_or_none()
        if order is None:
            raise not_found("Order not found")
        return order

    def _make_item(self, payload: OrderItemCreate, now: datetime) -> OrderItemModel:
        return OrderItemModel(
            sample_id=payload.sample_id,
            sample_name=payload.sample_name,
            lab_id=payload.lab_id,
            experiment_id=payload.experiment_id,
            status=OrderStatus.DRAFT.value,
            created_at=now,
            updated_at=now,
        )

    async def _validate_order_master_data(
        self,
        department_id: str,
        items: Sequence[OrderItemMasterData],
    ) -> None:
        department_exists = (
            await self.db.execute(
                select(Department.id).where(
                    Department.is_active.is_(True),
                    (cast(Department.id, String) == department_id)
                    | (Department.code == department_id),
                )
            )
        ).scalar_one_or_none()

        lab_ids = {item.lab_id for item in items}
        experiment_ids = {item.experiment_id for item in items}
        labs = (
            (
                await self.db.execute(
                    select(Lab).where(
                        Lab.is_active.is_(True),
                        (cast(Lab.id, String).in_(lab_ids)) | (Lab.code.in_(lab_ids)),
                    )
                )
            )
            .scalars()
            .all()
        )
        labs_by_key = {str(lab.id): lab for lab in labs}
        labs_by_key.update({lab.code: lab for lab in labs})

        capabilities = (
            (
                await self.db.execute(
                    select(LabCapability).where(cast(LabCapability.id, String).in_(experiment_ids))
                )
            )
            .scalars()
            .all()
        )
        capabilities_by_id = {str(capability.id): capability for capability in capabilities}

        if not department_exists:
            raise bad_request(f"Unknown department: {department_id}")

        for index, item in enumerate(items, start=1):
            lab = labs_by_key.get(item.lab_id)
            if lab is None:
                raise bad_request(f"Unknown lab in item {index}: {item.lab_id}")

            capability = capabilities_by_id.get(item.experiment_id)
            if capability is None:
                raise bad_request(f"Unknown experiment in item {index}: {item.experiment_id}")

            if capability.lab_id != lab.id:
                raise bad_request(
                    f"Experiment {item.experiment_id} does not belong to lab {item.lab_id}"
                )

    @staticmethod
    def _truncate_text(value: str | None, max_length: int) -> str | None:
        if value is None:
            return None
        if len(value) <= max_length:
            return value
        return value[: max_length - 1] + "…"

    def _append_history(
        self,
        order: OrderModel,
        actor_id: str,
        action: str,
        from_status: str | None,
        to_status: str,
        reason: str | None = None,
        quota_override: bool = False,
    ) -> None:
        self.db.add(
            OrderHistoryModel(
                order=order,
                actor_id=actor_id,
                action=action,
                from_status=from_status,
                to_status=to_status,
                reason=reason,
                quota_override=quota_override,
                action_time=utc_now(),
            )
        )

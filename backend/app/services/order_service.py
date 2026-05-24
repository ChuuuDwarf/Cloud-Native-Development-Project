from __future__ import annotations

from typing import Any

from app.common.dependencies import CurrentUser
from app.core.order_enums import OrderStatus
from app.db.models.order_management import QuotaSettingModel
from app.repos.order_repo import OrderRepository
from app.schemas.order import (
    Order,
    OrderActionRequest,
    OrderCreate,
    OrderHistory,
    OrderUpdate,
    QuotaPatchPayload,
    QuotaPayload,
)


class OrderService:
    """Application service for order workflows.

    Routes depend on this service instead of talking to the repository directly.
    The repository keeps persistence details; this layer is the stable business API
    for controllers/routes.
    """

    def __init__(self, repo: OrderRepository) -> None:
        self.repo = repo

    def create_order(self, payload: OrderCreate, current_user: CurrentUser) -> Order:
        return self.repo.create_order(payload, current_user)

    def list_orders(
        self,
        status_filter: OrderStatus | None = None,
        applicant_id: str | None = None,
        current_user: CurrentUser | None = None,
    ) -> list[Order]:
        return self.repo.list_orders(
            status_filter=status_filter,
            applicant_id=applicant_id,
            current_user=current_user,
        )

    def get_order(self, order_id: int) -> Order:
        return self.repo.get_order(order_id)

    def update_order(self, order_id: int, payload: OrderUpdate, current_user: CurrentUser) -> Order:
        return self.repo.update_order(order_id, payload, current_user)

    def delete_order(self, order_id: int, current_user: CurrentUser) -> None:
        self.repo.delete_order(order_id, current_user)

    def apply_action(
        self,
        order_id: int,
        payload: OrderActionRequest,
        current_user: CurrentUser,
    ) -> Order:
        return self.repo.apply_action(order_id, payload, current_user)

    def get_history(self, order_id: int) -> list[OrderHistory]:
        return self.repo.get_history(order_id)

    def list_quota_settings(self) -> list[QuotaSettingModel]:
        return self.repo.list_quota_settings()

    def create_quota_setting(self, payload: QuotaPayload) -> QuotaSettingModel:
        return self.repo.create_quota_setting(payload)

    def update_quota_setting(self, quota_id: int, payload: QuotaPatchPayload) -> QuotaSettingModel:
        return self.repo.update_quota_setting(quota_id, payload)

    def check_quota(
        self,
        applicant_id: str,
        department_id: str,
        item_count: int,
        priority: str = "normal",
    ) -> dict[str, Any]:
        return self.repo.check_quota(applicant_id, department_id, item_count, priority)

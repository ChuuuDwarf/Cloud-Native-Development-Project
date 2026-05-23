from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    applicant_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    department_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    apply_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="normal")
    total_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_reason: Mapped[str | None] = mapped_column(Text)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    items: Mapped[list[OrderItemModel]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderItemModel.id",
    )
    histories: Mapped[list[OrderHistoryModel]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderHistoryModel.id",
    )


class OrderItemModel(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    sample_id: Mapped[str] = mapped_column(String(50), nullable=False)
    lab_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    experiment_id: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    approved_by: Mapped[str | None] = mapped_column(String(50))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    return_reason: Mapped[str | None] = mapped_column(Text)
    reject_reason: Mapped[str | None] = mapped_column(Text)
    quota_exceeded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    quota_override: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    quota_override_reason: Mapped[str | None] = mapped_column(Text)
    quota_approved_by: Mapped[str | None] = mapped_column(String(50))
    quota_approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    order: Mapped[OrderModel] = relationship(back_populates="items")


class OrderHistoryModel(Base):
    __tablename__ = "order_histories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    actor_id: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(50))
    to_status: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    quota_override: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    action_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

    order: Mapped[OrderModel] = relationship(back_populates="histories")


class QuotaSettingModel(Base):
    __tablename__ = "quota_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    scope_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    scope_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    monthly_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    urgent_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    critical_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)


class QuotaUsageModel(Base):
    __tablename__ = "quota_usages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    scope_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    scope_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    month: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    urgent_used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    critical_used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)

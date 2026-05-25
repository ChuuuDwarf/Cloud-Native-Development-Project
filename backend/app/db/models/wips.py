"""WIP + WIP history models (ported from Role D's flat ``app/models.py``).

Async SQLAlchemy 2.0. Status strings store the canonical English enum values
from ``app.common.enums.WipStatus``. ``abort_status`` is a free-form string
(Role D embedded the abort request inside the WIP row).

Relationships are NOT lazy-loaded — repositories must eager-load ``history``
(and ``order.wips``) with ``selectinload``.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.orders import Order


class Wip(Base):
    __tablename__ = "wips"

    wip_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.order_id"))
    sample: Mapped[str] = mapped_column(String(64))
    experiment_item: Mapped[str] = mapped_column(String(64))
    machine_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    recipe: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32))
    progress: Mapped[int] = mapped_column(Integer, default=0)
    operator: Mapped[str | None] = mapped_column(String(32), nullable=True)
    check_in_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    check_out_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    result_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_data_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    data_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    # 中止申請（內嵌於 WIP）
    abort_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    abort_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
    abort_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    abort_requested_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    abort_resolution: Mapped[str | None] = mapped_column(Text, nullable=True)

    order: Mapped[Order] = relationship(back_populates="wips")
    history: Mapped[list[WipHistory]] = relationship(
        back_populates="wip",
        order_by="WipHistory.id",
        cascade="all, delete-orphan",
    )


class WipHistory(Base):
    __tablename__ = "wip_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    wip_id: Mapped[str] = mapped_column(ForeignKey("wips.wip_id"))
    time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    action: Mapped[str] = mapped_column(String(32))
    actor: Mapped[str] = mapped_column(String(32))
    note: Mapped[str] = mapped_column(Text, default="")

    wip: Mapped[Wip] = relationship(back_populates="history")

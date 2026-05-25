"""Order model (ported from Role D's flat ``app/models.py``).

Async SQLAlchemy 2.0. Role D's sync model used string PKs (e.g. ``ORD-001``)
and Chinese status strings stored verbatim; this port keeps the same column
shapes but stores the canonical English enum values from
``app.common.enums.OrderStatus``.

Relationships are NOT lazy-loaded — repositories must eager-load ``wips`` with
``selectinload`` (no lazy attribute access on an ``AsyncSession``).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.wips import Wip


class Order(Base):
    __tablename__ = "orders"

    order_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    applicant: Mapped[str] = mapped_column(String(64))
    factory: Mapped[str] = mapped_column(String(32))
    priority: Mapped[str] = mapped_column(String(16))
    experiment_item: Mapped[str] = mapped_column(String(64))
    lab: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))

    wips: Mapped[list[Wip]] = relationship(back_populates="order")

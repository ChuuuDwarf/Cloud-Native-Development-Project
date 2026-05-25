"""Storage + storage history models (ported from Role D's flat ``app/models.py``).

NOTE: distinct from ``app.db.models.storage_locations`` (table
``storage_locations``, owned by E). This is Role D's per-sample storage record
(table ``storage``) tracking inbound / outbound / pickup. Status strings store
the canonical English enum values from ``app.common.enums.StorageStatus``.

Relationships are NOT lazy-loaded — repositories must eager-load ``history``
with ``selectinload``.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Storage(Base):
    __tablename__ = "storage"

    storage_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    order_id: Mapped[str] = mapped_column(String(32), index=True)
    sample: Mapped[str] = mapped_column(String(64))
    qty: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32))
    location: Mapped[str] = mapped_column(String(32))

    history: Mapped[list[StorageHistory]] = relationship(
        back_populates="storage",
        order_by="StorageHistory.id",
        cascade="all, delete-orphan",
    )


class StorageHistory(Base):
    __tablename__ = "storage_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    storage_id: Mapped[str] = mapped_column(ForeignKey("storage.storage_id"))
    time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    action: Mapped[str] = mapped_column(String(32))
    actor: Mapped[str] = mapped_column(String(32))
    note: Mapped[str] = mapped_column(Text, default="")

    storage: Mapped[Storage] = relationship(back_populates="history")

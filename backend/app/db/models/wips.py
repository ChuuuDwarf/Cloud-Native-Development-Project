"""WIP + WIP history models — **B's canonical schema**.

組員 B owns the ``wips`` / ``wip_histories`` tables but ships them migration-only
(raw SQL, no ORM model). This module authors the ORM mapping from B's migration
``c65036646f0b`` so other modules (notably D's experiment_runs) can query via
SQLAlchemy. Column shapes mirror that migration exactly:

- surrogate UUID PK ``id``; business code in ``wip_no`` / ``order_no``
- ``status`` stores B's English enum values (DB CHECK constraint enforces them)

D's execution-only fields (machine/operator/result/abort …) are NOT here — they
live in the D-owned side table ``app.db.models.wip_execution.WipExecution``,
keyed by ``wip_no``. See [[cd-yields-to-ab-models]].

Relationships are NOT lazy-loaded — repositories must eager-load ``history``
with ``selectinload`` (no lazy attribute access on an ``AsyncSession``).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Wip(Base):
    __tablename__ = "wips"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4()
    )
    wip_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    # DB-level FK to samples.id exists (B's migration); not declared at the ORM
    # level because B ships ``samples`` migration-only (no ORM model to target).
    sample_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    order_no: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    lab_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    experiment_item: Mapped[str | None] = mapped_column(String(100), nullable=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, server_default="normal")
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default="created")
    progress: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    current_location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(TIMESTAMP, nullable=True)
    dispatched_at: Mapped[datetime | None] = mapped_column(TIMESTAMP, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP, nullable=True)
    terminated_at: Mapped[datetime | None] = mapped_column(TIMESTAMP, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Per-lab closure flag — set when this WIP's lab calls /closures/.../to-pickup.
    # The order itself only moves to WAITING_PICKUP once ALL of its WIPs are
    # ``lab_closed=True`` (i.e. every lab has signed off). DB column added in
    # migration 35aeb03a89e9; the ORM model was missing the field, which left
    # all reads/writes through other modules silent (Phase L review #3).
    lab_closed: Mapped[bool] = mapped_column(nullable=False, server_default="false", default=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name="wips_priority_check",
        ),
        CheckConstraint(
            """
            status IN (
                'created', 'waiting_schedule', 'scheduled', 'dispatched',
                'running', 'paused', 'completed', 'terminated', 'cancelled'
            )
            """,
            name="wips_status_check",
        ),
        CheckConstraint("progress >= 0 AND progress <= 100", name="wips_progress_check"),
    )

    history: Mapped[list[WipHistory]] = relationship(
        back_populates="wip",
        order_by="WipHistory.created_at",
        cascade="all, delete-orphan",
    )


class WipHistory(Base):
    __tablename__ = "wip_histories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4()
    )
    wip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wips.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    to_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    operator_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, nullable=False, server_default=func.now()
    )

    wip: Mapped[Wip] = relationship(back_populates="history")

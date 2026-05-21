"""Issue (異常 / 告警 / 中止申請) model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums import IssueStatus, IssueType, Severity
from app.db.base import Base, TimestampMixin


class Issue(Base, TimestampMixin):
    __tablename__ = "issues"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    type: Mapped[IssueType] = mapped_column(String(40), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    target_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    severity: Mapped[Severity] = mapped_column(String(20), nullable=False, default=Severity.MEDIUM)

    status: Mapped[IssueStatus] = mapped_column(
        String(20),
        nullable=False,
        default=IssueStatus.OPEN,
        index=True,
    )
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    escalation_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_escalation_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    handled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

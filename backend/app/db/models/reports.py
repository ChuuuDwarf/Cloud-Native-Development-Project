"""Report + version + attachment models (ported from Role D's flat ``app/models.py``).

Async SQLAlchemy 2.0. Status strings store the canonical English enum values
from ``app.common.enums.ReportStatus``.

Relationships are NOT lazy-loaded — repositories must eager-load ``versions`` /
``attachments`` with ``selectinload``.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Report(Base):
    __tablename__ = "reports"

    report_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    order_id: Mapped[str] = mapped_column(String(32))
    wip_id: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(128))
    summary: Mapped[str] = mapped_column(Text, default="")
    conclusion: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    created_by: Mapped[str] = mapped_column(String(32))

    versions: Mapped[list[ReportVersion]] = relationship(
        back_populates="report",
        order_by="ReportVersion.version",
        cascade="all, delete-orphan",
    )
    attachments: Mapped[list[ReportAttachment]] = relationship(
        back_populates="report",
        order_by="ReportAttachment.id",
        cascade="all, delete-orphan",
    )


class ReportVersion(Base):
    __tablename__ = "report_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[str] = mapped_column(ForeignKey("reports.report_id"))
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16))
    at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    actor: Mapped[str] = mapped_column(String(32))
    note: Mapped[str] = mapped_column(Text, default="")

    report: Mapped[Report] = relationship(back_populates="versions")


class ReportAttachment(Base):
    __tablename__ = "report_attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[str] = mapped_column(ForeignKey("reports.report_id"))
    name: Mapped[str] = mapped_column(String(128))
    at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    report: Mapped[Report] = relationship(back_populates="attachments")

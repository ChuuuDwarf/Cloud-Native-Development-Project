"""Lab + lab capability models."""

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Lab(Base, TimestampMixin):
    __tablename__ = "labs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    capabilities: Mapped[list["LabCapability"]] = relationship(
        back_populates="lab",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class LabCapability(Base, TimestampMixin):
    __tablename__ = "lab_capabilities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lab_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("labs.id", ondelete="CASCADE"),
        nullable=False,
    )
    experiment_item: Mapped[str] = mapped_column(String(120), nullable=False)

    lab: Mapped[Lab] = relationship(back_populates="capabilities")

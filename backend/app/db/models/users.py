"""User account model."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.enums import UserStatus
from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.labs import Lab
    from app.db.models.roles import Role


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Local phone for CHT TAS callout (Sprint 3d). Format: 09XXXXXXXX or
    # 0X-XXXXXXXX (no spaces / no symbols expected). Nullable because not
    # every account needs to receive phone alerts (e.g. system_admin).
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    lab_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("labs.id", ondelete="SET NULL"),
        nullable=True,
    )

    status: Mapped[UserStatus] = mapped_column(
        String(32),
        nullable=False,
        default=UserStatus.ACTIVE,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # No model-level lazy="selectin" — every caller already uses an explicit
    # selectinload(User.roles).selectinload(Role.permissions) chain because
    # they need the nested permissions too, which the model-level setting
    # can't express. Adding it here was an unconditional extra IN-query for
    # zero benefit.
    roles: Mapped[list["Role"]] = relationship(
        secondary="user_roles",
        back_populates="users",
    )
    lab: Mapped["Lab | None"] = relationship(lazy="selectin")

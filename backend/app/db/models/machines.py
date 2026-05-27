"""Machine / Recipe / Dispatch models (組員 C — 執行與機台).

Async SQLAlchemy 2.0. Each model has a UUID ``id`` PK plus a human-readable
natural-key string column (``machine_id`` / ``recipe_id`` / ``dispatch_id``),
mirroring the project pattern (see ``wips.py``).

Status strings store the Chinese display values the frontend expects (see the
module docstrings); the shared English enums in ``app.common.enums`` are left
untouched. List-shaped fields (``supported_items`` / ``machine_ids`` /
``parameters``) are stored as JSONB.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Machine(Base, TimestampMixin):
    __tablename__ = "machines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    machine_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    lab: Mapped[str] = mapped_column(String(64))
    # Chinese: 閒置 / 使用中 / 保養中 / 故障中 / 停用 (default 閒置)
    status: Mapped[str] = mapped_column(String(16), default="閒置")
    supported_items: Mapped[list[str]] = mapped_column(JSONB, default=list)
    utilization: Mapped[int] = mapped_column(Integer, default=0)
    owner: Mapped[str] = mapped_column(String(32), default="")
    last_maintenance: Mapped[str | None] = mapped_column(String(32), nullable=True)


class Recipe(Base, TimestampMixin):
    __tablename__ = "recipes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipe_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    version: Mapped[str] = mapped_column(String(32))
    experiment_item: Mapped[str] = mapped_column(String(64))
    machine_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)
    method: Mapped[str] = mapped_column(Text, default="")
    parameters: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict)
    updated_by: Mapped[str] = mapped_column(String(32), default="")


class Dispatch(Base, TimestampMixin):
    __tablename__ = "dispatches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dispatch_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    wip_id: Mapped[str] = mapped_column(String(32))
    order_id: Mapped[str] = mapped_column(String(32))
    experiment_item: Mapped[str] = mapped_column(String(64))
    priority: Mapped[str] = mapped_column(String(16))
    lab: Mapped[str] = mapped_column(String(64), default="")
    due_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Chinese: 待派工 / 排程中 / 待上機
    status: Mapped[str] = mapped_column(String(16), default="待派工")
    suggested_machine_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    assigned_machine_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    assigned_recipe_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    scheduled_start: Mapped[str | None] = mapped_column(String(32), nullable=True)
    scheduled_end: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
    assigned_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
    strategy: Mapped[str | None] = mapped_column(String(32), nullable=True)
    replan_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

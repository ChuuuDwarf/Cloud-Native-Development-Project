"""add order item sample name

Revision ID: d2c3e4f5a6b7
Revises: d1b2c3d4e5f6
Create Date: 2026-05-25 01:30:00.000000

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "d2c3e4f5a6b7"
down_revision: str | Sequence[str] | None = "d1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "order_items",
        sa.Column("sample_name", sa.String(length=100), nullable=True),
    )
    op.execute("UPDATE order_items SET sample_name = sample_id WHERE sample_name IS NULL")


def downgrade() -> None:
    op.drop_column("order_items", "sample_name")

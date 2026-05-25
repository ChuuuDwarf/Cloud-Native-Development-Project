"""merge heads + create machines / recipes / dispatches (組員 C)

Merges the two parallel heads (``0001`` and ``a14aa7269a7f``) into a single
head AND adds 組員 C's three tables.

Revision ID: 0002_c_machines
Revises: 0001, a14aa7269a7f
Create Date: 2026-05-24
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_c_machines"
down_revision: str | Sequence[str] | None = ("0001", "a14aa7269a7f")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "machines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("machine_id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("lab", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="閒置"),
        sa.Column("supported_items", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("utilization", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("owner", sa.String(length=32), nullable=False, server_default=""),
        sa.Column("last_maintenance", sa.String(length=32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("machine_id"),
    )
    op.create_index("ix_machines_machine_id", "machines", ["machine_id"])

    op.create_table(
        "recipes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recipe_id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("experiment_item", sa.String(length=64), nullable=False),
        sa.Column("machine_ids", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("method", sa.Text(), nullable=False, server_default=""),
        sa.Column("parameters", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("updated_by", sa.String(length=32), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("recipe_id"),
    )
    op.create_index("ix_recipes_recipe_id", "recipes", ["recipe_id"])

    op.create_table(
        "dispatches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dispatch_id", sa.String(length=32), nullable=False),
        sa.Column("wip_id", sa.String(length=32), nullable=False),
        sa.Column("order_id", sa.String(length=32), nullable=False),
        sa.Column("experiment_item", sa.String(length=64), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False),
        sa.Column("lab", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("due_at", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="待派工"),
        sa.Column("suggested_machine_id", sa.String(length=32), nullable=True),
        sa.Column("assigned_machine_id", sa.String(length=32), nullable=True),
        sa.Column("assigned_recipe_id", sa.String(length=32), nullable=True),
        sa.Column("scheduled_start", sa.String(length=32), nullable=True),
        sa.Column("scheduled_end", sa.String(length=32), nullable=True),
        sa.Column("created_by", sa.String(length=32), nullable=True),
        sa.Column("assigned_by", sa.String(length=32), nullable=True),
        sa.Column("strategy", sa.String(length=32), nullable=True),
        sa.Column("replan_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dispatch_id"),
    )
    op.create_index("ix_dispatches_dispatch_id", "dispatches", ["dispatch_id"])


def downgrade() -> None:
    op.drop_index("ix_dispatches_dispatch_id", table_name="dispatches")
    op.drop_table("dispatches")
    op.drop_index("ix_recipes_recipe_id", table_name="recipes")
    op.drop_table("recipes")
    op.drop_index("ix_machines_machine_id", table_name="machines")
    op.drop_table("machines")

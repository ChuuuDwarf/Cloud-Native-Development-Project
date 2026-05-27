"""add order item dependency fields

Revision ID: 0005_order_item_deps
Revises: 0004_d_exec_experiment_data
Create Date: 2026-05-27
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_order_item_deps"
down_revision = "0004_d_exec_experiment_data"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "order_items",
        sa.Column("target_group", sa.String(length=50), nullable=False, server_default="G1"),
    )
    op.add_column(
        "order_items",
        sa.Column("target", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "order_items",
        sa.Column("dependency_check", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_check_constraint(
        "order_items_target_positive_check",
        "order_items",
        "target >= 1",
    )

    op.create_index(
        "ix_order_items_dependency",
        "order_items",
        ["order_id", "sample_id", "target_group", "target"],
    )


def downgrade() -> None:
    op.drop_index("ix_order_items_dependency", table_name="order_items")
    op.drop_constraint("order_items_target_positive_check", "order_items", type_="check")
    op.drop_column("order_items", "dependency_check")
    op.drop_column("order_items", "target")
    op.drop_column("order_items", "target_group")

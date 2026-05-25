"""add order table

Revision ID: fea80b716b10
Revises: a14aa7269a7f
Create Date: 2026-05-23 17:54:06.680570

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "fea80b716b10"
down_revision: str | Sequence[str] | None = "a14aa7269a7f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("order_no", sa.String(length=50), nullable=False, unique=True),
        sa.Column("applicant_id", sa.String(length=50), nullable=False),
        sa.Column("department_id", sa.String(length=50), nullable=False),
        sa.Column("apply_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column(
            "priority",
            sa.String(length=20),
            nullable=False,
            server_default="normal",
        ),
        sa.Column(
            "total_items",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("last_reason", sa.Text(), nullable=True),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    op.create_index(
        "ix_orders_order_no",
        "orders",
        ["order_no"],
        unique=False,
    )
    op.create_index(
        "ix_orders_applicant_id",
        "orders",
        ["applicant_id"],
        unique=False,
    )
    op.create_index(
        "ix_orders_department_id",
        "orders",
        ["department_id"],
        unique=False,
    )
    op.create_index(
        "ix_orders_status",
        "orders",
        ["status"],
        unique=False,
    )

    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("sample_id", sa.String(length=50), nullable=False),
        sa.Column("sample_name", sa.String(length=100), nullable=True),
        sa.Column("lab_id", sa.String(length=50), nullable=False),
        sa.Column("experiment_id", sa.String(length=50), nullable=False),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("approved_by", sa.String(length=50), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("return_reason", sa.Text(), nullable=True),
        sa.Column("reject_reason", sa.Text(), nullable=True),
        sa.Column(
            "quota_exceeded",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
        sa.Column(
            "quota_override",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),

        # 這三個是你目前 code/model 會用到的欄位，原本 SQL 少了，這裡一併補上
        sa.Column("quota_override_reason", sa.Text(), nullable=True),
        sa.Column("quota_approved_by", sa.String(length=50), nullable=True),
        sa.Column("quota_approved_at", sa.DateTime(timezone=True), nullable=True),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            ondelete="CASCADE",
        ),
    )

    op.create_index(
        "ix_order_items_order_id",
        "order_items",
        ["order_id"],
        unique=False,
    )
    op.create_index(
        "ix_order_items_lab_id",
        "order_items",
        ["lab_id"],
        unique=False,
    )

    op.create_table(
        "order_histories",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.String(length=50), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("from_status", sa.String(length=50), nullable=True),
        sa.Column("to_status", sa.String(length=50), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "quota_override",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
        sa.Column(
            "action_time",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            ondelete="CASCADE",
        ),
    )

    op.create_index(
        "ix_order_histories_order_id",
        "order_histories",
        ["order_id"],
        unique=False,
    )

    op.create_table(
        "quota_settings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("scope_type", sa.String(length=30), nullable=False),
        sa.Column("scope_id", sa.String(length=50), nullable=False),
        sa.Column(
            "monthly_limit",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),

        # 這兩個是目前 code/model 會用到的欄位，原本 SQL 少了
        sa.Column("urgent_limit", sa.Integer(), nullable=True),
        sa.Column("critical_limit", sa.Integer(), nullable=True),

        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("TRUE"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    op.create_index(
        "ix_quota_settings_scope_type",
        "quota_settings",
        ["scope_type"],
        unique=False,
    )
    op.create_index(
        "ix_quota_settings_scope_id",
        "quota_settings",
        ["scope_id"],
        unique=False,
    )

    op.create_table(
        "quota_usages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("scope_type", sa.String(length=30), nullable=False),
        sa.Column("scope_id", sa.String(length=50), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column(
            "used_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),

        # 這兩個是目前 code/model 會用到的欄位，原本 SQL 少了
        sa.Column(
            "urgent_used_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "critical_used_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),

        sa.Column("order_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
        ),
    )

    op.create_index(
        "ix_quota_usages_scope_type",
        "quota_usages",
        ["scope_type"],
        unique=False,
    )
    op.create_index(
        "ix_quota_usages_scope_id",
        "quota_usages",
        ["scope_id"],
        unique=False,
    )
    op.create_index(
        "ix_quota_usages_year",
        "quota_usages",
        ["year"],
        unique=False,
    )
    op.create_index(
        "ix_quota_usages_month",
        "quota_usages",
        ["month"],
        unique=False,
    )
    op.create_index(
        "ix_quota_usages_order_id",
        "quota_usages",
        ["order_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_quota_usages_order_id", table_name="quota_usages")
    op.drop_index("ix_quota_usages_month", table_name="quota_usages")
    op.drop_index("ix_quota_usages_year", table_name="quota_usages")
    op.drop_index("ix_quota_usages_scope_id", table_name="quota_usages")
    op.drop_index("ix_quota_usages_scope_type", table_name="quota_usages")
    op.drop_table("quota_usages")

    op.drop_index("ix_quota_settings_scope_id", table_name="quota_settings")
    op.drop_index("ix_quota_settings_scope_type", table_name="quota_settings")
    op.drop_table("quota_settings")

    op.drop_index("ix_order_histories_order_id", table_name="order_histories")
    op.drop_table("order_histories")

    op.drop_index("ix_order_items_lab_id", table_name="order_items")
    op.drop_index("ix_order_items_order_id", table_name="order_items")
    op.drop_table("order_items")

    op.drop_index("ix_orders_status", table_name="orders")
    op.drop_index("ix_orders_department_id", table_name="orders")
    op.drop_index("ix_orders_applicant_id", table_name="orders")
    op.drop_index("ix_orders_order_no", table_name="orders")
    op.drop_table("orders")

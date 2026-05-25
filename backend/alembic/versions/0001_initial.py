"""initial schema: orders / wips / history / reports / storage

Revision ID: 0001
Revises:
Create Date: 2026-05-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("order_id", sa.String(32), primary_key=True),
        sa.Column("applicant", sa.String(64), nullable=False),
        sa.Column("factory", sa.String(32), nullable=False),
        sa.Column("priority", sa.String(16), nullable=False),
        sa.Column("experiment_item", sa.String(64), nullable=False),
        sa.Column("lab", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
    )

    op.create_table(
        "wips",
        sa.Column("wip_id", sa.String(32), primary_key=True),
        sa.Column("order_id", sa.String(32), sa.ForeignKey("orders.order_id"), nullable=False),
        sa.Column("sample", sa.String(64), nullable=False),
        sa.Column("experiment_item", sa.String(64), nullable=False),
        sa.Column("machine_id", sa.String(32), nullable=True),
        sa.Column("recipe", sa.String(32), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("operator", sa.String(32), nullable=True),
        sa.Column("check_in_at", sa.DateTime(), nullable=True),
        sa.Column("check_out_at", sa.DateTime(), nullable=True),
        sa.Column("result_note", sa.Text(), nullable=True),
        sa.Column("raw_data_url", sa.String(255), nullable=True),
        sa.Column("data_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("abort_reason", sa.Text(), nullable=True),
        sa.Column("abort_by", sa.String(32), nullable=True),
        sa.Column("abort_status", sa.String(16), nullable=True),
        sa.Column("abort_requested_at", sa.DateTime(), nullable=True),
        sa.Column("abort_resolution", sa.Text(), nullable=True),
    )

    op.create_table(
        "wip_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("wip_id", sa.String(32), sa.ForeignKey("wips.wip_id"), nullable=False),
        sa.Column("time", sa.DateTime(), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("actor", sa.String(32), nullable=False),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
    )

    op.create_table(
        "reports",
        sa.Column("report_id", sa.String(32), primary_key=True),
        sa.Column("order_id", sa.String(32), nullable=False),
        sa.Column("wip_id", sa.String(32), nullable=False),
        sa.Column("title", sa.String(128), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("conclusion", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.String(32), nullable=False),
    )

    op.create_table(
        "report_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("report_id", sa.String(32), sa.ForeignKey("reports.report_id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("at", sa.DateTime(), nullable=False),
        sa.Column("actor", sa.String(32), nullable=False),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
    )

    op.create_table(
        "report_attachments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("report_id", sa.String(32), sa.ForeignKey("reports.report_id"), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "storage",
        sa.Column("storage_id", sa.String(32), primary_key=True),
        sa.Column("order_id", sa.String(32), nullable=False),
        sa.Column("sample", sa.String(64), nullable=False),
        sa.Column("qty", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("location", sa.String(32), nullable=False),
    )

    op.create_table(
        "storage_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("storage_id", sa.String(32), sa.ForeignKey("storage.storage_id"), nullable=False),
        sa.Column("time", sa.DateTime(), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("actor", sa.String(32), nullable=False),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_table("storage_history")
    op.drop_table("storage")
    op.drop_table("report_attachments")
    op.drop_table("report_versions")
    op.drop_table("reports")
    op.drop_table("wip_history")
    op.drop_table("wips")
    op.drop_table("orders")

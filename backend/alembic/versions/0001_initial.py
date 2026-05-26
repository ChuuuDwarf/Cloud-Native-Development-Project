"""D-owned tables: reports / report_versions / report_attachments / storage /
storage_history / wip_execution

Originally this revision (a second Alembic root) also created ``orders`` / ``wips``
/ ``wip_history``. Those duplicated A's ``orders`` and B's ``wips`` and have been
removed — D now reuses A's ``OrderModel`` and B's ``wips`` via business codes
``order_no`` / ``wip_no``. D's execution-only fields moved to the ``wip_execution``
side table. See [[cd-yields-to-ab-models]].

Re-parented onto B's head so the chain is linear:
E(a14aa7269a7f) -> A(fea80b716b10) -> B(c65036646f0b) -> 0001 -> 0002.

Revision ID: 0001
Revises: c65036646f0b
Create Date: 2026-05-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = "c65036646f0b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # reports.order_id / wip_id store A/B business codes (order_no / wip_no);
    # no FK to A/B tables (those use surrogate PKs).
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
        sa.Column("order_id", sa.String(32), nullable=False, index=True),
        sa.Column("sample", sa.String(64), nullable=False),
        sa.Column("qty", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
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

    # D-owned execution side table, keyed 1:1 to B's wips by business code wip_no.
    op.create_table(
        "wip_execution",
        sa.Column("wip_no", sa.String(50), primary_key=True),
        sa.Column(
            "exec_status", sa.String(20), nullable=False, server_default="waiting_load"
        ),
        sa.Column("machine_id", sa.String(32), nullable=True),
        sa.Column("recipe", sa.String(32), nullable=True),
        sa.Column("operator", sa.String(64), nullable=True),
        sa.Column("check_in_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("check_out_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("result_note", sa.Text(), nullable=True),
        sa.Column("raw_data_url", sa.String(255), nullable=True),
        sa.Column("data_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("abort_status", sa.String(16), nullable=True),
        sa.Column("abort_reason", sa.Text(), nullable=True),
        sa.Column("abort_by", sa.String(64), nullable=True),
        sa.Column("abort_requested_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("abort_resolution", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("NOW()")),
    )


def downgrade() -> None:
    op.drop_table("wip_execution")
    op.drop_table("storage_history")
    op.drop_table("storage")
    op.drop_table("report_attachments")
    op.drop_table("report_versions")
    op.drop_table("reports")

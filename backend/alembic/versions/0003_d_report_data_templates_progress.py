"""D: report experiment_data + report_templates + wip_execution.next_progress_at

Adds three D-owned changes (no A/B tables touched):
- ``reports.experiment_data`` (JSON) — auto-generated measurement data per
  experiment item.
- ``report_templates`` table — saved report skeletons (referencing 委託單).
- ``wip_execution.next_progress_at`` — schedule for the background progress
  auto-advance task.

Chains after C's ``0002_c_machines``.

Revision ID: 0003_d_report_progress
Revises: 0002_c_machines
Create Date: 2026-05-26
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_d_report_progress"
down_revision: str | Sequence[str] | None = "0002_c_machines"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("reports", sa.Column("experiment_data", sa.JSON(), nullable=True))
    op.add_column(
        "wip_execution",
        sa.Column("next_progress_at", sa.TIMESTAMP(), nullable=True),
    )
    op.create_table(
        "report_templates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("order_id", sa.String(length=32), nullable=True),
        sa.Column("summary", sa.Text(), server_default="", nullable=False),
        sa.Column("conclusion", sa.Text(), server_default="", nullable=False),
        sa.Column("created_by", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("report_templates")
    op.drop_column("wip_execution", "next_progress_at")
    op.drop_column("reports", "experiment_data")

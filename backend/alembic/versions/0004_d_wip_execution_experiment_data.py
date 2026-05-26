"""D: wip_execution.experiment_data — persist measured data at machine completion

- ``wip_execution.experiment_data`` (JSON) — the measurement data the machine
  collected, generated once when the WIP enters 待確認 (machine completion /
  result upload). Shown at 驗證數據 and reused by the report (so it no longer
  re-randomises on every report create).

Create Date: 2026-05-26
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_d_exec_experiment_data"
down_revision: str | Sequence[str] | None = "0003_d_report_progress"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("wip_execution", sa.Column("experiment_data", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("wip_execution", "experiment_data")

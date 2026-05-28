"""0007_e_add_lab_closed_to_wips

Revision ID: 35aeb03a89e9
Revises: 358991d2b30b
Create Date: 2026-05-28 21:10:01.701207

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "35aeb03a89e9"
down_revision: str | Sequence[str] | None = "358991d2b30b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
      op.add_column(
          "wips",
          sa.Column(
              "lab_closed",
              sa.Boolean(),
              nullable=False,
              server_default=sa.text("false"),
          ),
      )


def downgrade() -> None:
    op.drop_column("wips", "lab_closed")
    # ### end Alembic commands ###

"""0006 e add phone to users

Revision ID: ed4c240792c2
Revises: 999b46431692
Create Date: 2026-05-27 00:36:29.768614

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ed4c240792c2"
down_revision: str | Sequence[str] | None = "999b46431692"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
      op.add_column("users", sa.Column("phone", sa.String(20), nullable=True))

def downgrade() -> None:
    op.drop_column("users", "phone")

### end Alembic commands ###

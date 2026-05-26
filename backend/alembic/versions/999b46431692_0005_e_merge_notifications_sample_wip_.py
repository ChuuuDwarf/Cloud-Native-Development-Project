"""0005 e merge notifications + sample_wip heads

Revision ID: 999b46431692
Revises: af4cd2be5b6b, c65036646f0b
Create Date: 2026-05-26 16:38:48.069845

"""

from __future__ import annotations

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "999b46431692"
down_revision: str | Sequence[str] | None = ("af4cd2be5b6b", "c65036646f0b")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

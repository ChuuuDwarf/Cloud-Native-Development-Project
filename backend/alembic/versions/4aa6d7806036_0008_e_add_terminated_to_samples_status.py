"""0008_e_add_terminated_to_samples_status

Add 'terminated' to the ``samples.status`` CHECK list so the
``review_abort`` -> ``_advance_sample_on_termination`` helper can flip
the sample's status when every sibling WIP is terminated. The original
CHECK (from c65036646f0b_create_sample_wip_management_tables) hard-codes
the allowed values and rejected the UPDATE -- the abort committed but
the sample stayed on 'split' and /sample showed stale state.

Revision ID: 4aa6d7806036
Revises: 35aeb03a89e9
Create Date: 2026-05-30 21:17:58.427551

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4aa6d7806036"
down_revision: str | Sequence[str] | None = "35aeb03a89e9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Postgres has no ALTER CHECK CONSTRAINT -- drop and recreate.
    op.drop_constraint("samples_status_check", "samples", type_="check")
    op.create_check_constraint(
        "samples_status_check",
        "samples",
        """
        status IN (
            'pending_receive',
            'received',
            'split',
            'pending_transfer',
            'transferring',
            'in_storage',
            'outbound',
            'picked_up',
            'lost',
            'damaged',
            'cancelled',
            'terminated'
        )
        """,
    )


def downgrade() -> None:
    op.drop_constraint("samples_status_check", "samples", type_="check")
    op.create_check_constraint(
        "samples_status_check",
        "samples",
        """
        status IN (
            'pending_receive',
            'received',
            'split',
            'pending_transfer',
            'transferring',
            'in_storage',
            'outbound',
            'picked_up',
            'lost',
            'damaged',
            'cancelled'
        )
        """,
    )

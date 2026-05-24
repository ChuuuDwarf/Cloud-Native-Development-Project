"""repair sample completed status

Revision ID: d1b2c3d4e5f6
Revises: c65036646f0b
Create Date: 2026-05-25 00:00:00.000000

"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op


revision: str = "d1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "c65036646f0b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # completed 是 WIP 狀態，不是 Sample 狀態；修復舊資料避免分貨頁消失。
    op.execute("UPDATE samples SET status = 'split' WHERE status = 'completed'")

    op.execute("ALTER TABLE samples DROP CONSTRAINT IF EXISTS samples_status_check")
    op.execute(
        """
        ALTER TABLE samples
        ADD CONSTRAINT samples_status_check
        CHECK (
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
        )
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE samples DROP CONSTRAINT IF EXISTS samples_status_check")
    op.execute(
        """
        ALTER TABLE samples
        ADD CONSTRAINT samples_status_check
        CHECK (
            status IN (
                'pending_receive',
                'received',
                'split',
                'pending_transfer',
                'transferring',
                'completed',
                'in_storage',
                'outbound',
                'picked_up',
                'lost',
                'damaged',
                'cancelled'
            )
        )
        """
    )

"""create sample wip management tables

Revision ID: c65036646f0b
Revises: fea80b716b10
Create Date: 2026-05-24 17:32:03.342739

"""

from __future__ import annotations
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "c65036646f0b"
down_revision: str | Sequence[str] | None = "fea80b716b10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.create_table(
        "samples",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("sample_no", sa.String(length=50), nullable=False, unique=True),
        sa.Column("order_no", sa.String(length=50), nullable=False),
        sa.Column("sample_name", sa.String(length=100), nullable=True),
        sa.Column("experiment_item", sa.String(length=100), nullable=True),
        sa.Column("applicant_name", sa.String(length=100), nullable=True),
        sa.Column("applicant_department", sa.String(length=100), nullable=True),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'pending_receive'"),
        ),
        sa.Column("current_location", sa.String(length=100), nullable=True),
        sa.Column("storage_location_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("received_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("received_by", sa.String(length=100), nullable=True),
        sa.Column("picked_up_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("picked_up_by", sa.String(length=100), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["storage_location_id"], ["storage_locations.id"]),
        sa.CheckConstraint(
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
            name="samples_status_check",
        ),
    )

    op.create_table(
        "sample_histories",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("sample_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("from_status", sa.String(length=50), nullable=True),
        sa.Column("to_status", sa.String(length=50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("operator_name", sa.String(length=100), nullable=True),
        sa.Column("lab_name", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["sample_id"], ["samples.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "transfers",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("transfer_no", sa.String(length=50), nullable=False, unique=True),
        sa.Column("target_type", sa.String(length=20), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_no", sa.String(length=50), nullable=True),
        sa.Column("sample_no", sa.String(length=50), nullable=True),
        sa.Column("wip_no", sa.String(length=50), nullable=True),
        sa.Column("from_lab", sa.String(length=100), nullable=False),
        sa.Column("to_lab", sa.String(length=100), nullable=False),
        sa.Column("handed_by", sa.String(length=100), nullable=True),
        sa.Column("received_by", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("transferred_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("received_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint(
            "target_type IN ('sample', 'wip')",
            name="transfers_target_type_check",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'transferring', 'received', 'cancelled')",
            name="transfers_status_check",
        ),
    )

    op.create_table(
        "wips",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("wip_no", sa.String(length=50), nullable=False, unique=True),
        sa.Column("sample_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_no", sa.String(length=50), nullable=False),
        sa.Column("lab_name", sa.String(length=100), nullable=True),
        sa.Column("experiment_item", sa.String(length=100), nullable=True),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default=sa.text("'normal'")),
        sa.Column("status", sa.String(length=30), nullable=False, server_default=sa.text("'created'")),
        sa.Column("progress", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("current_location", sa.String(length=100), nullable=True),
        sa.Column("scheduled_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("dispatched_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("started_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("terminated_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["sample_id"], ["samples.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name="wips_priority_check",
        ),
        sa.CheckConstraint(
            """
            status IN (
                'created',
                'waiting_schedule',
                'scheduled',
                'dispatched',
                'running',
                'paused',
                'completed',
                'terminated',
                'cancelled'
            )
            """,
            name="wips_status_check",
        ),
        sa.CheckConstraint(
            "progress >= 0 AND progress <= 100",
            name="wips_progress_check",
        ),
    )

    op.create_table(
        "wip_histories",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("wip_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("from_status", sa.String(length=30), nullable=True),
        sa.Column("to_status", sa.String(length=30), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("operator_name", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("NOW()")),
        sa.ForeignKeyConstraint(["wip_id"], ["wips.id"], ondelete="CASCADE"),
    )

    op.create_index("idx_samples_order_no", "samples", ["order_no"])
    op.create_index("idx_samples_status", "samples", ["status"])
    op.create_index("idx_samples_sample_no", "samples", ["sample_no"])

    op.create_index("idx_sample_histories_sample_id", "sample_histories", ["sample_id"])

    op.create_index("idx_transfers_target", "transfers", ["target_type", "target_id"])
    op.create_index("idx_transfers_order_no", "transfers", ["order_no"])
    op.create_index("idx_transfers_status", "transfers", ["status"])
    op.create_index("idx_transfers_target_id", "transfers", ["target_id"])

    op.create_index("idx_wips_order_no", "wips", ["order_no"])
    op.create_index("idx_wips_status", "wips", ["status"])
    op.create_index("idx_wips_sample_id", "wips", ["sample_id"])

    op.create_index("idx_wip_histories_wip_id", "wip_histories", ["wip_id"])


def downgrade():
    op.drop_index("idx_wip_histories_wip_id", table_name="wip_histories")

    op.drop_index("idx_wips_sample_id", table_name="wips")
    op.drop_index("idx_wips_status", table_name="wips")
    op.drop_index("idx_wips_order_no", table_name="wips")

    op.drop_index("idx_transfers_target_id", table_name="transfers")
    op.drop_index("idx_transfers_status", table_name="transfers")
    op.drop_index("idx_transfers_order_no", table_name="transfers")
    op.drop_index("idx_transfers_target", table_name="transfers")

    op.drop_index("idx_sample_histories_sample_id", table_name="sample_histories")

    op.drop_index("idx_samples_sample_no", table_name="samples")
    op.drop_index("idx_samples_status", table_name="samples")
    op.drop_index("idx_samples_order_no", table_name="samples")

    op.drop_table("wip_histories")
    op.drop_table("wips")
    op.drop_table("transfers")
    op.drop_table("sample_histories")
    op.drop_table("samples")
    op.drop_table("storage_locations")

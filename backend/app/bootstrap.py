from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db.base import Base


def bootstrap_database(sync_engine: Engine) -> None:
    Base.metadata.create_all(bind=sync_engine)

    alter_statements = [
        """
        ALTER TABLE order_items
        ADD COLUMN IF NOT EXISTS status VARCHAR(50) NOT NULL DEFAULT 'draft'
        """,
        """
        ALTER TABLE order_items
        ADD COLUMN IF NOT EXISTS approved_by VARCHAR(50)
        """,
        """
        ALTER TABLE order_items
        ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ
        """,
        """
        ALTER TABLE order_items
        ADD COLUMN IF NOT EXISTS return_reason TEXT
        """,
        """
        ALTER TABLE order_items
        ADD COLUMN IF NOT EXISTS reject_reason TEXT
        """,
        """
        ALTER TABLE order_items
        ADD COLUMN IF NOT EXISTS quota_exceeded BOOLEAN NOT NULL DEFAULT FALSE
        """,
        """
        ALTER TABLE order_items
        ADD COLUMN IF NOT EXISTS quota_override BOOLEAN NOT NULL DEFAULT FALSE
        """,
        """
        ALTER TABLE order_items
        ADD COLUMN IF NOT EXISTS quota_override_reason TEXT
        """,
        """
        ALTER TABLE order_items
        ADD COLUMN IF NOT EXISTS quota_approved_by VARCHAR(50)
        """,
        """
        ALTER TABLE order_items
        ADD COLUMN IF NOT EXISTS quota_approved_at TIMESTAMPTZ
        """,
        """
        UPDATE order_items
        SET status = 'draft'
        WHERE status IS NULL
        """,
    ]

    with sync_engine.begin() as connection:
        for statement in alter_statements:
            connection.execute(text(statement))

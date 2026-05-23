from __future__ import annotations

from sqlalchemy import text

from app.db.base import Base
from app.db.session import sync_engine


def create_database_tables() -> None:
    Base.metadata.create_all(bind=sync_engine)
    with sync_engine.begin() as connection:
        connection.execute(text("ALTER TABLE order_items ADD COLUMN IF NOT EXISTS status VARCHAR(50) NOT NULL DEFAULT 'draft'"))
        connection.execute(text("ALTER TABLE order_items ADD COLUMN IF NOT EXISTS approved_by VARCHAR(50)"))
        connection.execute(text("ALTER TABLE order_items ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ"))
        connection.execute(text("ALTER TABLE order_items ADD COLUMN IF NOT EXISTS return_reason TEXT"))
        connection.execute(text("ALTER TABLE order_items ADD COLUMN IF NOT EXISTS reject_reason TEXT"))
        connection.execute(text("ALTER TABLE order_items ADD COLUMN IF NOT EXISTS quota_exceeded BOOLEAN NOT NULL DEFAULT FALSE"))
        connection.execute(text("ALTER TABLE order_items ADD COLUMN IF NOT EXISTS quota_override BOOLEAN NOT NULL DEFAULT FALSE"))
        connection.execute(text("ALTER TABLE order_items ADD COLUMN IF NOT EXISTS quota_override_reason TEXT"))
        connection.execute(text("ALTER TABLE order_items ADD COLUMN IF NOT EXISTS quota_approved_by VARCHAR(50)"))
        connection.execute(text("ALTER TABLE order_items ADD COLUMN IF NOT EXISTS quota_approved_at TIMESTAMPTZ"))
        connection.execute(text("UPDATE order_items SET status = 'draft' WHERE status IS NULL"))

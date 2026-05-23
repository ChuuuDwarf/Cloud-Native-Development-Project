from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def generate_order_no(order_id: int) -> str:
    date_text = utc_now().strftime("%Y%m%d")
    suffix = f"{order_id:03d}-{uuid4().hex[:4].upper()}"
    return f"ORD-{date_text}-{suffix}"

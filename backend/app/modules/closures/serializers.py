"""camelCase serializers for closures responses.

Ported from Role D's flat ``app/models.py`` (``storage_dict`` / ``event_dict``).
Kept in the module (the project has no central ``app/serializers.py``); output
shape matches the frontend ``lib/types.ts`` contract.
"""

from __future__ import annotations

from datetime import datetime

from app.db.models import Storage, StorageHistory

TIME_FMT = "%Y-%m-%d %H:%M:%S"


def fmt(dt: datetime | None) -> str | None:
    return dt.strftime(TIME_FMT) if dt else None


def event_dict(h: StorageHistory) -> dict:
    return {"time": fmt(h.time), "action": h.action, "by": h.actor, "note": h.note}


def storage_dict(s: Storage) -> dict:
    return {
        "storageId": s.storage_id,
        "orderId": s.order_id,
        "sample": s.sample,
        "qty": s.qty,
        "status": s.status,
        "location": s.location,
        "history": [event_dict(h) for h in s.history],
    }

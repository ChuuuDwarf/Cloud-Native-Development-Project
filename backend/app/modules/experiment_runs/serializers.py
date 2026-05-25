"""camelCase serializers for experiment-runs responses.

Ported from Role D's flat ``app/models.py`` (``wip_dict`` / ``event_dict``).
Output shape matches the frontend contract.
"""

from __future__ import annotations

from datetime import datetime

from app.db.models import Wip, WipHistory

TIME_FMT = "%Y-%m-%d %H:%M:%S"


def fmt(dt: datetime | None) -> str | None:
    return dt.strftime(TIME_FMT) if dt else None


def history_dict(h: WipHistory) -> dict:
    return {"time": fmt(h.time), "action": h.action, "by": h.actor, "note": h.note}


def wip_dict(w: Wip) -> dict:
    abort = None
    if w.abort_status:
        abort = {
            "reason": w.abort_reason,
            "by": w.abort_by,
            "status": w.abort_status,
            "requestedAt": fmt(w.abort_requested_at),
            "resolution": w.abort_resolution,
        }
    return {
        "wipId": w.wip_id,
        "orderId": w.order_id,
        "sample": w.sample,
        "experimentItem": w.experiment_item,
        "machineId": w.machine_id,
        "recipe": w.recipe,
        "status": w.status,
        "progress": w.progress,
        "operator": w.operator,
        "checkInAt": fmt(w.check_in_at),
        "checkOutAt": fmt(w.check_out_at),
        "resultNote": w.result_note,
        "rawDataUrl": w.raw_data_url,
        "dataVerified": w.data_verified,
        "abort": abort,
        "history": [history_dict(h) for h in w.history],
    }

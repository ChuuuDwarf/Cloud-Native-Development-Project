"""camelCase serializers for experiment-runs responses.

Combines B's ``Wip`` row with D's ``WipExecution`` side row into the single
shape D's frontend expects (Chinese ``status`` rendered from the fine-grained
``exec_status``). ``wip_execution`` may be absent for a WIP that has not yet
entered D's flow — treated as ``waiting_load``.
"""

from __future__ import annotations

from datetime import datetime

from app.common.enums import WipStatus
from app.common.enums.role_d_zh import WIP_ZH
from app.db.models import Wip, WipExecution, WipHistory

TIME_FMT = "%Y-%m-%d %H:%M:%S"


def fmt(dt: datetime | None) -> str | None:
    return dt.strftime(TIME_FMT) if dt else None


# B 的粗粒度 wips.status → 中文。WIP 還沒進入 D 執行流程（無 exec 列）時，
# 顯示它在 A→B→C 鏈上的真實階段，而不是一律「待上機」——否則一個還沒派工的
# WIP 會誤顯示待上機、給出上機鈕卻被後端關卡擋下。只有 dispatched 才是待上機。
_B_COARSE_ZH = {
    "created": "已建立",
    "waiting_schedule": "待派工",
    "scheduled": "排程中",
    "dispatched": "待上機",
    "running": "執行中",
    "paused": "暫停",
    "completed": "已完成",
    "terminated": "已終止",
    "cancelled": "已取消",
}


def _status_zh(w: Wip, exec_row: WipExecution | None) -> str:
    if exec_row is None:
        return _B_COARSE_ZH.get(w.status, w.status)
    try:
        return WIP_ZH[WipStatus(exec_row.exec_status)]
    except (ValueError, KeyError):
        return exec_row.exec_status


def history_dict(h: WipHistory) -> dict:
    return {
        "time": fmt(h.created_at),
        "action": h.action,
        "by": h.operator_name,
        "note": h.description,
    }


def wip_dict(
    w: Wip,
    exec_row: WipExecution | None,
    planned: tuple[str | None, str | None] | None = None,
) -> dict:
    """Serialize a WIP (+ optional exec row).

    ``planned`` is the ``(machine_id, recipe)`` the dispatch已指派 (from C's
    ``dispatches``); used as a fallback so the 上機 form can pre-fill the planned
    machine/Recipe before an exec row exists (待上機). The exec row, once present,
    takes precedence. See [[cd-flow-chain-enforced]].
    """
    planned_machine, planned_recipe = planned or (None, None)
    abort = None
    if exec_row and exec_row.abort_status:
        abort = {
            "reason": exec_row.abort_reason,
            "by": exec_row.abort_by,
            "status": exec_row.abort_status,
            "requestedAt": fmt(exec_row.abort_requested_at),
            "resolution": exec_row.abort_resolution,
        }
    return {
        "wipId": w.wip_no,
        "orderId": w.order_no,
        # TODO(sample-name): B's wips has only sample_id (UUID); resolve the
        # display name via a samples join if the UI needs it.
        "sample": None,
        "experimentItem": w.experiment_item,
        "machineId": (exec_row.machine_id if exec_row else None) or planned_machine,
        "recipe": (exec_row.recipe if exec_row else None) or planned_recipe,
        "status": _status_zh(w, exec_row),
        "progress": w.progress,
        "operator": exec_row.operator if exec_row else None,
        "checkInAt": fmt(exec_row.check_in_at) if exec_row else None,
        "checkOutAt": fmt(exec_row.check_out_at) if exec_row else None,
        "resultNote": exec_row.result_note if exec_row else None,
        "rawDataUrl": exec_row.raw_data_url if exec_row else None,
        "experimentData": (exec_row.experiment_data if exec_row else None) or {},
        "dataVerified": exec_row.data_verified if exec_row else False,
        "abort": abort,
        "history": [history_dict(h) for h in w.history],
    }

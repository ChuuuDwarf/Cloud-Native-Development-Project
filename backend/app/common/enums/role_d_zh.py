"""Legacy Chinese status-string maps for Role D's modules.

Role D's three backend modules (``experiment_runs``, ``reports`` and
``closures``) store WIP / order / report / storage statuses in the database as
the ORIGINAL Chinese display strings (e.g. ``wips.status = "執行中"``,
``orders.status = "實驗中"``, ``reports.status = "草稿"``,
``storage.status = "已入庫"``) rather than the canonical English enum values
used everywhere else in ``app.common.enums``.

These maps translate each canonical enum member to the Chinese string actually
persisted, so Role D's services can compare and assign statuses against the
real stored values. They are a temporary bridge until the demo data is migrated
to the canonical English enum values; once that migration happens these maps
(and their use sites) can be removed.

Pure data module — no logic. The shared enums themselves are NOT changed: other
modules (e.g. module B's ``wips``) rely on the English values.
"""

from __future__ import annotations

from app.common.enums import OrderStatus, ReportStatus, StorageStatus, WipStatus

WIP_ZH: dict[WipStatus, str] = {
    WipStatus.WAITING_LOAD: "待上機",
    WipStatus.RUNNING: "執行中",
    WipStatus.UNLOADED: "已下機",
    WipStatus.WAITING_CONFIRM: "待確認",
    WipStatus.COMPLETED: "已完成",
    WipStatus.TERMINATED: "已終止",
}

ORDER_ZH: dict[OrderStatus, str] = {
    OrderStatus.SCHEDULED: "排程中",
    OrderStatus.IN_PROGRESS: "實驗中",
    OrderStatus.WAITING_RESULT_CONFIRM: "待結果確認",
    OrderStatus.COMPLETED: "已完成",
    OrderStatus.WAITING_REPORT_RETURN: "待報告回傳",
    OrderStatus.WAITING_PICKUP: "待取件",
    OrderStatus.CLOSED: "已結案",
}

REPORT_ZH: dict[ReportStatus, str] = {
    ReportStatus.DRAFT: "草稿",
    ReportStatus.PENDING_REVIEW: "待審核",
    ReportStatus.CONFIRMED: "已確認",
    ReportStatus.PUBLISHED: "已發布",
    ReportStatus.RETURNED: "已回傳",
    ReportStatus.REVISED: "已改版",
}

STORAGE_ZH: dict[StorageStatus, str] = {
    StorageStatus.IN_LAB: "實驗室",
    StorageStatus.STORED: "已入庫",
    StorageStatus.PENDING_RETURN: "待返還",
    StorageStatus.PICKED_UP: "已取件",
}

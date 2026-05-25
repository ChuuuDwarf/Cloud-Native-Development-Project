"""Idempotent Role D demo seed: orders + WIPs (+history) + reports + storage.

Run from ``backend/`` (after ``alembic upgrade head`` and AFTER ``seed_dev``)::

    python -m scripts.seed_experiments

Re-runs safely: every row is upserted by natural key (order_id / wip_id /
report_id / storage_id). WIP / order / report / storage statuses are stored as
the ORIGINAL Chinese display strings (the values Role D's services compare
against) — see ``app.common.enums.role_d_zh`` for the canonical map.

This recreates the original Role D demo dataset as a committed, reproducible
seed so the execution / report / closure pages render a realistic mix of
states.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import selectinload

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.db.models import (  # noqa: E402
    Order,
    Report,
    ReportVersion,
    Storage,
    StorageHistory,
    Wip,
    WipHistory,
)

# ---------------------------------------------------------------------------
# Status strings — stored verbatim in Chinese (see app.common.enums.role_d_zh).
# WIP    : 待上機 / 執行中 / 已下機 / 待確認 / 已完成 / 已終止
# Order  : 排程中 / 實驗中 / 待結果確認 / 已完成 / 待報告回傳 / 待取件 / 已結案
# Report : 草稿 / 待審核 / 已確認 / 已發布 / 已回傳 / 已改版
# Storage: 實驗室 / 已入庫 / 待返還 / 已取件
# ---------------------------------------------------------------------------


def _dt(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# Orders — natural key: order_id. applicant / factory / priority /
# experiment_item / lab are all non-null.
# ---------------------------------------------------------------------------

# order_id, applicant, factory, priority, experiment_item, lab, status
ORDERS: list[tuple[str, str, str, str, str, str, str]] = [
    ("WO-2024-0891", "陳明德", "Fab-A", "高", "IC電性", "電性測試實驗室", "實驗中"),
    ("WO-2024-0892", "李工", "Fab-A", "中", "光學量測", "材料分析實驗室", "實驗中"),
    ("WO-2024-0893", "張建平", "Fab-B", "中", "化學分析", "材料分析實驗室", "已完成"),
    ("WO-2024-0894", "張建平", "Fab-B", "高", "熱阻分析", "可靠度實驗室", "已完成"),
    ("WO-2024-0895", "林佳慧", "Fab-A", "高", "SEM分析", "材料分析實驗室", "已完成"),
    ("WO-2024-0896", "張建平", "Fab-B", "中", "X-Ray", "電性測試實驗室", "待取件"),
]


# ---------------------------------------------------------------------------
# WIPs — natural key: wip_id. Each dict carries an optional "history" list of
# (action, actor, note) tuples seeded in order.
# ---------------------------------------------------------------------------

WIPS: list[dict] = [
    {
        "wip_id": "WIP-0891-01",
        "order_id": "WO-2024-0891",
        "sample": "晶圓#A-1",
        "experiment_item": "IC電性",
        "machine_id": "TEM-001",
        "recipe": "RCP-TEM-v2.3",
        "status": "執行中",
        "progress": 72,
        "operator": "陳明德",
        "check_in_at": _dt("2026-05-21 09:00:00"),
        "history": [
            ("上機", "陳明德", "機台 TEM-001 / RCP-TEM-v2.3"),
            ("更新進度", "陳明德", "72%"),
        ],
    },
    {
        "wip_id": "WIP-0891-02",
        "order_id": "WO-2024-0891",
        "sample": "晶圓#A-2",
        "experiment_item": "電阻量測",
        "machine_id": "XRD-002",
        "recipe": "RCP-XRD-v1.5",
        "status": "待確認",
        "progress": 100,
        "operator": "陳明德",
        "check_in_at": _dt("2026-05-21 09:00:00"),
        "check_out_at": _dt("2026-05-21 12:27:01"),
        "result_note": "機台 XRD-002 自動回報完成，數據已寫入，待人員驗證",
        "raw_data_url": "/data/WIP-0891-02.auto.csv",
        "data_verified": False,
        "history": [
            ("上機", "陳明德", "機台 XRD-002 / RCP-XRD-v1.5"),
            ("下機", "系統(機台)", "機台回報完成自動下機"),
            ("機台自動數據蒐集", "系統(機台)", "已寫入原始數據，進入待結果確認"),
        ],
    },
    {
        "wip_id": "WIP-0892-01",
        "order_id": "WO-2024-0892",
        "sample": "玻璃基板",
        "experiment_item": "光學量測",
        "machine_id": "OPT-001",
        "recipe": "RCP-OPT-v2.0",
        "status": "執行中",
        "progress": 0,
        "operator": "李工",
        "check_in_at": _dt("2026-05-21 12:26:56"),
        "history": [
            ("上機", "李工", "機台 OPT-001 / RCP-OPT-v2.0"),
        ],
    },
    {
        "wip_id": "WIP-0893-01",
        "order_id": "WO-2024-0893",
        "sample": "化學試片",
        "experiment_item": "化學分析",
        "machine_id": "CHM-001",
        "recipe": "RCP-CHM-v1.2",
        "status": "已完成",
        "progress": 100,
        "operator": "張建平",
        "check_in_at": _dt("2026-05-19 09:00:00"),
        "result_note": "成份比例符合需求",
        "data_verified": True,
        "history": [
            ("上機", "張建平", "機台 CHM-001 / RCP-CHM-v1.2"),
        ],
    },
    {
        "wip_id": "WIP-0894-01",
        "order_id": "WO-2024-0894",
        "sample": "銅導線框架",
        "experiment_item": "熱阻分析",
        "machine_id": "THR-001",
        "recipe": "RCP-THR-v1.0",
        "status": "已完成",
        "progress": 100,
        "operator": "張建平",
        "check_in_at": _dt("2026-05-21 09:00:00"),
        "check_out_at": _dt("2026-05-21 11:30:00"),
        "result_note": "熱阻量測完成，數值在規格內",
        "raw_data_url": "/data/WIP-0894-01.csv",
        "data_verified": True,
        "history": [
            ("上機", "張建平", "機台 THR-001 / RCP-THR-v1.0"),
            ("下機", "張建平", "實驗完成"),
            ("上傳結果", "張建平", "待人員確認"),
            ("確認結果", "張建平", "熱阻量測完成，數值在規格內"),
        ],
    },
    {
        "wip_id": "WIP-0895-01",
        "order_id": "WO-2024-0895",
        "sample": "金屬片",
        "experiment_item": "SEM分析",
        "machine_id": "SEM-001",
        "recipe": "RCP-SEM-v3.1",
        "status": "已終止",
        "progress": 60,
        "operator": "林佳慧",
        "check_in_at": _dt("2026-05-21 09:00:00"),
        "result_note": "影像偏移，疑似載台異常",
        "data_verified": False,
        "abort_reason": "SEM 影像數據異常，需人工判定",
        "abort_by": "林佳慧",
        "abort_status": "已終止",
        "abort_requested_at": _dt("2026-05-21 11:00:00"),
        "abort_resolution": "終止",
        "history": [
            ("上機", "林佳慧", "機台 SEM-001 / RCP-SEM-v3.1"),
            ("下機", "林佳慧", "數據異常待確認"),
            ("主管核准終止", "實驗室主管", "終止"),
        ],
    },
    {
        "wip_id": "WIP-0896-01",
        "order_id": "WO-2024-0896",
        "sample": "玻璃基板",
        "experiment_item": "X-Ray",
        "machine_id": "XRD-002",
        "recipe": "RCP-XRD-v1.5",
        "status": "已完成",
        "progress": 100,
        "operator": "張建平",
        "check_in_at": _dt("2026-05-20 14:00:00"),
        "check_out_at": _dt("2026-05-20 16:00:00"),
        "result_note": "X-Ray 影像清晰，無異常",
        "data_verified": True,
        "history": [
            ("上機", "張建平", "機台 XRD-002 / RCP-XRD-v1.5"),
        ],
    },
]


# ---------------------------------------------------------------------------
# Reports — natural key: report_id. Linked to completed / confirmed WIPs'
# orders. "versions" is a list of (version, status, actor, note).
# ---------------------------------------------------------------------------

REPORTS: list[dict] = [
    {
        "report_id": "RPT-0893-01",
        "order_id": "WO-2024-0893",
        "wip_id": "WIP-0893-01",
        "title": "化學分析報告 - 化學試片",
        "summary": "成份比例量測，符合規格需求。",
        "conclusion": "結論：合格。",
        "status": "草稿",
        "created_by": "張建平",
        "versions": [
            (1, "草稿", "張建平", "建立草稿"),
        ],
    },
    {
        "report_id": "RPT-0894-01",
        "order_id": "WO-2024-0894",
        "wip_id": "WIP-0894-01",
        "title": "熱阻分析報告 - 銅導線框架",
        "summary": "熱阻量測完成，數值在規格內。",
        "conclusion": "結論：合格，建議結案。",
        "status": "待審核",
        "created_by": "張建平",
        "versions": [
            (1, "草稿", "張建平", "建立草稿"),
            (2, "待審核", "張建平", "送出審核"),
        ],
    },
    {
        "report_id": "RPT-0896-01",
        "order_id": "WO-2024-0896",
        "wip_id": "WIP-0896-01",
        "title": "X-Ray 檢測報告 - 玻璃基板",
        "summary": "X-Ray 影像清晰，無異常。",
        "conclusion": "結論：無異常，待客戶取件。",
        "status": "已回傳",
        "created_by": "張建平",
        "versions": [
            (1, "草稿", "張建平", "建立草稿"),
            (2, "待審核", "張建平", "送出審核"),
            (3, "已回傳", "實驗室主管", "已回傳委託方"),
        ],
    },
]


# ---------------------------------------------------------------------------
# Storage — natural key: storage_id. "history" is (action, actor, note).
# ---------------------------------------------------------------------------

STORAGE: list[dict] = [
    {
        "storage_id": "STO-0893-01",
        "order_id": "WO-2024-0893",
        "sample": "化學試片",
        "qty": "1 片",
        "status": "已入庫",
        "location": "STG-A2",
        "history": [
            ("入庫", "張建平", "化學分析完成後入庫"),
        ],
    },
    {
        "storage_id": "STO-0894-01",
        "order_id": "WO-2024-0894",
        "sample": "銅導線框架",
        "qty": "2 件",
        "status": "待返還",
        "location": "STG-A2",
        "history": [
            ("入庫", "張建平", "熱阻分析完成後入庫"),
            ("申請返還", "張建平", "委託方要求返還樣品"),
        ],
    },
    {
        "storage_id": "STO-0896-01",
        "order_id": "WO-2024-0896",
        "sample": "玻璃基板",
        "qty": "1 片",
        "status": "已取件",
        "location": "STG-B1",
        "history": [
            ("入庫", "張建平", "X-Ray 完成後入庫"),
            ("取件", "張建平", "委託方已取件"),
        ],
    },
]


# ---------------------------------------------------------------------------
# Upsert helpers — natural-key idempotent. History/version children are
# rebuilt (cleared + reseeded) so a re-run never duplicates child rows.
# ---------------------------------------------------------------------------


async def upsert_order(session, row: tuple[str, str, str, str, str, str, str]) -> None:
    order_id, applicant, factory, priority, experiment_item, lab, status = row
    existing = (
        await session.execute(select(Order).where(Order.order_id == order_id))
    ).scalar_one_or_none()
    if existing:
        existing.applicant = applicant
        existing.factory = factory
        existing.priority = priority
        existing.experiment_item = experiment_item
        existing.lab = lab
        existing.status = status
        return
    session.add(
        Order(
            order_id=order_id,
            applicant=applicant,
            factory=factory,
            priority=priority,
            experiment_item=experiment_item,
            lab=lab,
            status=status,
        )
    )
    await session.flush()


async def upsert_wip(session, spec: dict) -> None:
    history = spec.get("history", [])
    fields = {k: v for k, v in spec.items() if k != "history"}

    wip = (
        await session.execute(
            select(Wip).options(selectinload(Wip.history)).where(Wip.wip_id == spec["wip_id"])
        )
    ).scalar_one_or_none()

    if wip is None:
        wip = Wip(**fields)
        session.add(wip)
        await session.flush()
    else:
        for key, value in fields.items():
            setattr(wip, key, value)
        wip.history.clear()
        await session.flush()

    base = wip.check_in_at or datetime.now()
    for action, actor, note in history:
        session.add(
            WipHistory(
                wip_id=wip.wip_id,
                time=base,
                action=action,
                actor=actor,
                note=note,
            )
        )
    await session.flush()


async def upsert_report(session, spec: dict) -> None:
    versions = spec.get("versions", [])
    fields = {k: v for k, v in spec.items() if k != "versions"}

    report = (
        await session.execute(
            select(Report)
            .options(selectinload(Report.versions))
            .where(Report.report_id == spec["report_id"])
        )
    ).scalar_one_or_none()

    if report is None:
        report = Report(**fields)
        session.add(report)
        await session.flush()
    else:
        for key, value in fields.items():
            setattr(report, key, value)
        report.versions.clear()
        await session.flush()

    for version, status, actor, note in versions:
        session.add(
            ReportVersion(
                report_id=report.report_id,
                version=version,
                status=status,
                actor=actor,
                note=note,
            )
        )
    await session.flush()


async def upsert_storage(session, spec: dict) -> None:
    history = spec.get("history", [])
    fields = {k: v for k, v in spec.items() if k != "history"}

    storage = (
        await session.execute(
            select(Storage)
            .options(selectinload(Storage.history))
            .where(Storage.storage_id == spec["storage_id"])
        )
    ).scalar_one_or_none()

    if storage is None:
        storage = Storage(**fields)
        session.add(storage)
        await session.flush()
    else:
        for key, value in fields.items():
            setattr(storage, key, value)
        storage.history.clear()
        await session.flush()

    for action, actor, note in history:
        session.add(
            StorageHistory(
                storage_id=storage.storage_id,
                action=action,
                actor=actor,
                note=note,
            )
        )
    await session.flush()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> None:
    async with AsyncSessionLocal() as session:
        for order_row in ORDERS:
            await upsert_order(session, order_row)
        for wip_spec in WIPS:
            await upsert_wip(session, wip_spec)
        for report_spec in REPORTS:
            await upsert_report(session, report_spec)
        for storage_spec in STORAGE:
            await upsert_storage(session, storage_spec)
        await session.commit()

    sys.stdout.write(
        "Role D demo seed complete.\n"
        f"  orders : {len(ORDERS)}\n"
        f"  wips   : {len(WIPS)}\n"
        f"  reports: {len(REPORTS)}\n"
        f"  storage: {len(STORAGE)}\n"
    )


if __name__ == "__main__":
    asyncio.run(main())

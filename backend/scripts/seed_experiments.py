"""Idempotent Role D demo seed: samples + orders + WIPs (+history + execution)
+ reports + storage.

Run from ``backend/`` (after ``alembic upgrade head`` and AFTER ``seed_dev``)::

    python -m scripts.seed_experiments

Re-runs safely: every row is upserted by natural key (order_no / sample_no /
wip_no / report_id / storage_id).

Schema note (post four-functions merge — see ``app.common.enums.role_d_zh`` and
[[cd-yields-to-ab-models]]):
- Orders use **A's** ``OrderModel`` (business code ``order_no``; English status).
- WIPs use **B's** ``wips`` (UUID PK, FK to ``samples``; coarse English status),
  so each WIP needs a backing ``samples`` row. D's fine-grained execution status
  + machine/result/abort fields live in the D-owned ``wip_execution`` side table.
- Reports / storage are D-owned; their statuses stay the original Chinese.

This script bridges the original Chinese demo statuses to the canonical English
values on write.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.common.enums import OrderStatus, WipStatus  # noqa: E402
from app.common.enums.role_d_zh import ORDER_ZH, WIP_EXEC_TO_B, WIP_ZH  # noqa: E402
from app.core.database import AsyncSessionLocal  # noqa: E402
from app.db.models import (  # noqa: E402
    OrderModel,
    Report,
    ReportVersion,
    Storage,
    StorageHistory,
    Wip,
    WipExecution,
    WipHistory,
)

# Chinese demo string -> canonical enum (reverse of the role_d_zh maps).
_ZH_TO_WIP = {zh: status for status, zh in WIP_ZH.items()}
_ZH_TO_ORDER = {zh: status for status, zh in ORDER_ZH.items()}
_PRIORITY_ZH_TO_EN = {"高": "high", "中": "normal", "低": "low", "緊急": "urgent"}


def _dt(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")


def _wip_enum(zh: str) -> WipStatus:
    return _ZH_TO_WIP.get(zh, WipStatus.WAITING_LOAD)


# ---------------------------------------------------------------------------
# Orders — natural key: order_no. (applicant / department stored as plain demo
# strings; A's columns are non-null but D's pages only need order_no + status.)
# ---------------------------------------------------------------------------

# order_no, applicant, factory(->department), priority(zh), experiment_item, lab, status(zh)
ORDERS: list[tuple[str, str, str, str, str, str, str]] = [
    ("WO-2024-0891", "陳明德", "Fab-A", "高", "IC電性", "電性測試實驗室", "實驗中"),
    ("WO-2024-0892", "李工", "Fab-A", "中", "光學量測", "材料分析實驗室", "實驗中"),
    ("WO-2024-0893", "張建平", "Fab-B", "中", "化學分析", "材料分析實驗室", "已完成"),
    ("WO-2024-0894", "張建平", "Fab-B", "高", "熱阻分析", "可靠度實驗室", "已完成"),
    ("WO-2024-0895", "林佳慧", "Fab-A", "高", "SEM分析", "材料分析實驗室", "已完成"),
    ("WO-2024-0896", "張建平", "Fab-B", "中", "X-Ray", "電性測試實驗室", "待取件"),
]


# ---------------------------------------------------------------------------
# WIPs — natural key: wip_no. Each spec also seeds a backing samples row and a
# wip_execution side row. "history" is a list of (action, actor, note) tuples.
# ---------------------------------------------------------------------------

WIPS: list[dict] = [
    {
        "wip_no": "WIP-0891-01",
        "order_no": "WO-2024-0891",
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
        "wip_no": "WIP-0891-02",
        "order_no": "WO-2024-0891",
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
        "wip_no": "WIP-0892-01",
        "order_no": "WO-2024-0892",
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
        "wip_no": "WIP-0893-01",
        "order_no": "WO-2024-0893",
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
        "wip_no": "WIP-0894-01",
        "order_no": "WO-2024-0894",
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
        "wip_no": "WIP-0895-01",
        "order_no": "WO-2024-0895",
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
        "wip_no": "WIP-0896-01",
        "order_no": "WO-2024-0896",
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
# Reports / Storage — D-owned tables; statuses stay the original Chinese.
# order_id / wip_id columns hold A/B business codes (order_no / wip_no).
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
        "versions": [(1, "草稿", "張建平", "建立草稿")],
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

STORAGE: list[dict] = [
    {
        "storage_id": "STO-0893-01",
        "order_id": "WO-2024-0893",
        "sample": "化學試片",
        "qty": "1 片",
        "status": "已入庫",
        "location": "STG-A2",
        "history": [("入庫", "張建平", "化學分析完成後入庫")],
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
# Upsert helpers — natural-key idempotent.
# ---------------------------------------------------------------------------


async def upsert_order(session, row: tuple[str, str, str, str, str, str, str]) -> None:
    order_no, applicant, factory, priority_zh, _experiment_item, _lab, status_zh = row
    status_en = _ZH_TO_ORDER.get(status_zh, OrderStatus.IN_PROGRESS).value
    priority_en = _PRIORITY_ZH_TO_EN.get(priority_zh, "normal")
    existing = (
        await session.execute(select(OrderModel).where(OrderModel.order_no == order_no))
    ).scalar_one_or_none()
    if existing:
        existing.applicant_id = applicant
        existing.department_id = factory
        existing.status = status_en
        existing.priority = priority_en
        return
    session.add(
        OrderModel(
            order_no=order_no,
            applicant_id=applicant,
            department_id=factory,
            apply_date=datetime.now(),
            status=status_en,
            priority=priority_en,
            total_items=1,
        )
    )
    await session.flush()


async def upsert_wip(session, spec: dict) -> None:
    """Seed the backing sample, B's wip, the wip_execution side row, and history."""
    wip_no = spec["wip_no"]
    order_no = spec["order_no"]
    wip_enum = _wip_enum(spec["status"])

    # 1) backing sample (B) — natural key sample_no = SMP-<wip_no>
    sample_no = f"SMP-{wip_no}"
    sample_id = await _ensure_sample(
        session, sample_no, order_no, spec["sample"], spec["experiment_item"]
    )

    # 2) WIP (B) — coarse status from the fine-grained demo status
    coarse = WIP_EXEC_TO_B[wip_enum]
    wip = (
        await session.execute(
            select(Wip).options(selectinload(Wip.history)).where(Wip.wip_no == wip_no)
        )
    ).scalar_one_or_none()
    wip_fields = {
        "wip_no": wip_no,
        "sample_id": sample_id,
        "order_no": order_no,
        "experiment_item": spec["experiment_item"],
        "status": coarse,
        "progress": spec.get("progress", 0),
        "started_at": spec.get("check_in_at"),
        "completed_at": spec.get("check_out_at"),
        "terminated_at": (
            spec.get("abort_requested_at") if wip_enum is WipStatus.TERMINATED else None
        ),
    }
    if wip is None:
        wip = Wip(**wip_fields)
        session.add(wip)
        await session.flush()
    else:
        for key, value in wip_fields.items():
            setattr(wip, key, value)
        wip.history.clear()
        await session.flush()

    # 3) execution side row (D)
    exec_row = await session.get(WipExecution, wip_no)
    exec_fields = {
        "exec_status": wip_enum.value,
        "machine_id": spec.get("machine_id"),
        "recipe": spec.get("recipe"),
        "operator": spec.get("operator"),
        "check_in_at": spec.get("check_in_at"),
        "check_out_at": spec.get("check_out_at"),
        "result_note": spec.get("result_note"),
        "raw_data_url": spec.get("raw_data_url"),
        "data_verified": spec.get("data_verified", False),
        "abort_status": spec.get("abort_status"),
        "abort_reason": spec.get("abort_reason"),
        "abort_by": spec.get("abort_by"),
        "abort_requested_at": spec.get("abort_requested_at"),
        "abort_resolution": spec.get("abort_resolution"),
    }
    if exec_row is None:
        session.add(WipExecution(wip_no=wip_no, **exec_fields))
    else:
        for key, value in exec_fields.items():
            setattr(exec_row, key, value)
    await session.flush()

    # 4) history (B's wip_histories: action / operator_name / description)
    for action, actor, note in spec.get("history", []):
        session.add(WipHistory(wip_id=wip.id, action=action, operator_name=actor, description=note))
    await session.flush()


async def _ensure_sample(
    session, sample_no: str, order_no: str, sample_name: str, experiment_item: str
):
    """Upsert a minimal B ``samples`` row and return its UUID id.

    B ships ``samples`` migration-only (no ORM model), so we use raw SQL.
    """
    existing = (
        await session.execute(
            text("SELECT id FROM samples WHERE sample_no = :sn"), {"sn": sample_no}
        )
    ).first()
    if existing:
        return existing[0]
    result = await session.execute(
        text(
            "INSERT INTO samples (sample_no, order_no, sample_name, experiment_item, status) "
            "VALUES (:sn, :on, :nm, :ei, 'received') RETURNING id"
        ),
        {"sn": sample_no, "on": order_no, "nm": sample_name, "ei": experiment_item},
    )
    await session.flush()
    return result.scalar_one()


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
            StorageHistory(storage_id=storage.storage_id, action=action, actor=actor, note=note)
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
        f"  wips   : {len(WIPS)} (+ samples + execution rows)\n"
        f"  reports: {len(REPORTS)}\n"
        f"  storage: {len(STORAGE)}\n"
    )


if __name__ == "__main__":
    asyncio.run(main())

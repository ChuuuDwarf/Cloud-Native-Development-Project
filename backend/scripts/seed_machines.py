"""Idempotent 組員 C demo seed: machines + recipes + dispatches.

Run from ``backend/`` (after ``alembic upgrade heads``)::

    python -m scripts.seed_machines

Re-runs safely: every row is upserted by natural key (machine_id / recipe_id /
dispatch_id). Status values are stored verbatim in Chinese:
    Machine : 閒置 / 使用中 / 保養中 / 故障中 / 停用
    Dispatch: 待排程 / 待派工 / 待上機

Data is aligned with the existing experiment seed (scripts/seed_experiments.py)
so labs / items / machines / recipes line up.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.db.models import Dispatch, Machine, Recipe  # noqa: E402

LAB = "LAB-A"

# machine_id, name, supported_items, owner, status, utilization, last_maintenance
MACHINES: list[dict] = [
    {
        "machine_id": "TEM-001",
        "name": "穿透式電子顯微鏡",
        "supported_items": ["IC電性"],
        "owner": "陳明德",
        "status": "使用中",
        "utilization": 82,
        "last_maintenance": "2026-05-10",
    },
    {
        "machine_id": "XRD-002",
        "name": "X-ray 繞射儀",
        "supported_items": ["電阻量測", "X-Ray"],
        "owner": "陳明德",
        "status": "使用中",
        "utilization": 67,
        "last_maintenance": "2026-05-08",
    },
    {
        "machine_id": "SEM-001",
        "name": "掃描式電子顯微鏡",
        "supported_items": ["SEM分析"],
        "owner": "林佳慧",
        "status": "保養中",
        "utilization": 45,
        "last_maintenance": "2026-05-20",
    },
    {
        "machine_id": "THR-001",
        "name": "熱阻分析儀",
        "supported_items": ["熱阻分析"],
        "owner": "張建平",
        "status": "閒置",
        "utilization": 30,
        "last_maintenance": "2026-04-28",
    },
    {
        "machine_id": "OPT-001",
        "name": "光學量測儀",
        "supported_items": ["光學量測"],
        "owner": "李工",
        "status": "使用中",
        "utilization": 58,
        "last_maintenance": "2026-05-12",
    },
    {
        "machine_id": "CHM-001",
        "name": "化學分析儀",
        "supported_items": ["化學分析"],
        "owner": "張建平",
        "status": "閒置",
        "utilization": 22,
        "last_maintenance": "2026-05-02",
    },
    # 對應 seed_experiments 的樣品實驗項目（EDX / IV / TC），讓既有 demo WIP 也能派工。
    {
        "machine_id": "EDX-001",
        "name": "能量散射光譜儀",
        "supported_items": ["EDX"],
        "owner": "林佳慧",
        "status": "閒置",
        "utilization": 18,
        "last_maintenance": "2026-05-15",
    },
    {
        "machine_id": "IV-001",
        "name": "半導體參數量測儀",
        "supported_items": ["IV"],
        "owner": "陳明德",
        "status": "閒置",
        "utilization": 35,
        "last_maintenance": "2026-05-14",
    },
    {
        "machine_id": "TC-001",
        "name": "溫度循環試驗機",
        "supported_items": ["TC"],
        "owner": "張建平",
        "status": "閒置",
        "utilization": 27,
        "last_maintenance": "2026-05-11",
    },
]

# recipe_id, name, version, experiment_item, machine_ids, method, parameters, updated_by
RECIPES: list[dict] = [
    {
        "recipe_id": "RCP-TEM-v2.3",
        "name": "IC 電性量測 Recipe",
        "version": "v2.3",
        "experiment_item": "IC電性",
        "machine_ids": ["TEM-001"],
        "method": "穿透式電子顯微鏡電性掃描",
        "parameters": {"電壓": "200kV", "放大倍率": "50000x", "時間": "30min"},
        "updated_by": "陳明德",
    },
    {
        "recipe_id": "RCP-XRD-v1.5",
        "name": "X-Ray 繞射量測 Recipe",
        "version": "v1.5",
        "experiment_item": "X-Ray",
        "machine_ids": ["XRD-002"],
        "method": "X-ray 繞射掃描 + 電阻量測",
        "parameters": {"掃描角度": "10-80度", "步進": "0.02度", "電流": "40mA"},
        "updated_by": "陳明德",
    },
    {
        "recipe_id": "RCP-SEM-v3.1",
        "name": "SEM 影像分析 Recipe",
        "version": "v3.1",
        "experiment_item": "SEM分析",
        "machine_ids": ["SEM-001"],
        "method": "掃描式電子顯微鏡影像擷取",
        "parameters": {"加速電壓": "15kV", "工作距離": "10mm", "放大倍率": "10000x"},
        "updated_by": "林佳慧",
    },
    {
        "recipe_id": "RCP-THR-v1.0",
        "name": "熱阻量測 Recipe",
        "version": "v1.0",
        "experiment_item": "熱阻分析",
        "machine_ids": ["THR-001"],
        "method": "穩態熱阻量測",
        "parameters": {"功率": "5W", "環境溫度": "25度", "量測時間": "60min"},
        "updated_by": "張建平",
    },
    {
        "recipe_id": "RCP-OPT-v2.0",
        "name": "光學量測 Recipe",
        "version": "v2.0",
        "experiment_item": "光學量測",
        "machine_ids": ["OPT-001"],
        "method": "穿透 / 反射光譜量測",
        "parameters": {"波長範圍": "300-1100nm", "解析度": "1nm"},
        "updated_by": "李工",
    },
    {
        "recipe_id": "RCP-CHM-v1.2",
        "name": "化學成份分析 Recipe",
        "version": "v1.2",
        "experiment_item": "化學分析",
        "machine_ids": ["CHM-001"],
        "method": "ICP 成份定量分析",
        "parameters": {"樣品量": "10mg", "稀釋倍率": "100x"},
        "updated_by": "張建平",
    },
    {
        "recipe_id": "RCP-EDX-v1.0",
        "name": "EDX 成份分析 Recipe",
        "version": "v1.0",
        "experiment_item": "EDX",
        "machine_ids": ["EDX-001"],
        "method": "能量散射光譜成份定量",
        "parameters": {"加速電壓": "20kV", "取樣時間": "60s"},
        "updated_by": "林佳慧",
    },
    {
        "recipe_id": "RCP-IV-v1.0",
        "name": "IV 特性量測 Recipe",
        "version": "v1.0",
        "experiment_item": "IV",
        "machine_ids": ["IV-001"],
        "method": "電流-電壓特性掃描",
        "parameters": {"電壓範圍": "-5V~5V", "步進": "0.1V"},
        "updated_by": "陳明德",
    },
    {
        "recipe_id": "RCP-TC-v1.0",
        "name": "溫度循環試驗 Recipe",
        "version": "v1.0",
        "experiment_item": "TC",
        "machine_ids": ["TC-001"],
        "method": "高低溫循環應力試驗",
        "parameters": {"溫度範圍": "-40~125度", "循環數": "500"},
        "updated_by": "張建平",
    },
]

# Dispatches — mixed states. 待排程 (no suggestion), 待派工 (with suggestion),
# 待上機 (fully assigned). Items all map to a supporting machine.
DISPATCHES: list[dict] = [
    {
        "dispatch_id": "DSP-0897-01",
        "wip_id": "WIP-0897-01",
        "order_id": "WO-2024-0897",
        "experiment_item": "IC電性",
        "priority": "高",
        "lab": LAB,
        "due_at": "2026-05-28",
        "status": "待排程",
        "created_by": "林佳慧",
    },
    {
        "dispatch_id": "DSP-0897-02",
        "wip_id": "WIP-0897-02",
        "order_id": "WO-2024-0897",
        "experiment_item": "化學分析",
        "priority": "中",
        "lab": LAB,
        "due_at": "2026-05-30",
        "status": "待排程",
        "created_by": "林佳慧",
    },
    {
        "dispatch_id": "DSP-0898-01",
        "wip_id": "WIP-0898-01",
        "order_id": "WO-2024-0898",
        "experiment_item": "SEM分析",
        "priority": "高",
        "lab": LAB,
        "due_at": "2026-05-27",
        "status": "待派工",
        "suggested_machine_id": "SEM-001",
        "strategy": "Priority First",
        "created_by": "林佳慧",
    },
    {
        "dispatch_id": "DSP-0899-01",
        "wip_id": "WIP-0899-01",
        "order_id": "WO-2024-0899",
        "experiment_item": "熱阻分析",
        "priority": "中",
        "lab": LAB,
        "due_at": "2026-05-26",
        "status": "待上機",
        "suggested_machine_id": "THR-001",
        "assigned_machine_id": "THR-001",
        "assigned_recipe_id": "RCP-THR-v1.0",
        "scheduled_start": "2026-05-25 09:00",
        "scheduled_end": "2026-05-25 11:00",
        "strategy": "FIFO",
        "created_by": "林佳慧",
        "assigned_by": "張建平",
    },
]


async def upsert_machine(session, spec: dict) -> None:
    existing = (
        await session.execute(select(Machine).where(Machine.machine_id == spec["machine_id"]))
    ).scalar_one_or_none()
    fields = {**spec, "lab": LAB}
    if existing:
        for key, value in fields.items():
            setattr(existing, key, value)
        return
    session.add(Machine(**fields))
    await session.flush()


async def upsert_recipe(session, spec: dict) -> None:
    existing = (
        await session.execute(select(Recipe).where(Recipe.recipe_id == spec["recipe_id"]))
    ).scalar_one_or_none()
    if existing:
        for key, value in spec.items():
            setattr(existing, key, value)
        return
    session.add(Recipe(**spec))
    await session.flush()


# Optional workflow columns reset to a baseline on every re-run, so a re-seed
# is a true reset regardless of any prior mutation (assign / suggest / replan).
_DISPATCH_RESETTABLE: dict[str, object] = {
    "suggested_machine_id": None,
    "assigned_machine_id": None,
    "assigned_recipe_id": None,
    "scheduled_start": None,
    "scheduled_end": None,
    "assigned_by": None,
    "strategy": None,
    "replan_reason": None,
}


async def upsert_dispatch(session, spec: dict) -> None:
    existing = (
        await session.execute(select(Dispatch).where(Dispatch.dispatch_id == spec["dispatch_id"]))
    ).scalar_one_or_none()
    # Spec values win; any resettable column not in the spec falls back to baseline.
    fields = {**_DISPATCH_RESETTABLE, **spec}
    if existing:
        for key, value in fields.items():
            setattr(existing, key, value)
        return
    session.add(Dispatch(**fields))
    await session.flush()


async def main() -> None:
    async with AsyncSessionLocal() as session:
        for spec in MACHINES:
            await upsert_machine(session, spec)
        for spec in RECIPES:
            await upsert_recipe(session, spec)
        for spec in DISPATCHES:
            await upsert_dispatch(session, spec)
        await session.commit()

    sys.stdout.write(
        "組員 C demo seed complete.\n"
        f"  machines  : {len(MACHINES)}\n"
        f"  recipes   : {len(RECIPES)}\n"
        f"  dispatches: {len(DISPATCHES)}\n"
    )


if __name__ == "__main__":
    asyncio.run(main())

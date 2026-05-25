"""Shared workflow helpers for sample / WIP / transfer flows.

These helpers are intentionally independent from app.services.temporary_others_service
so production workflow services do not depend on the temporary Others module.
"""

import json
from typing import Any

from fastapi import HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def row_to_dict(row):
    return dict(row._mapping)


def lab_location(lab_name: str | None, area: str):
    if not lab_name:
        return area

    lab_name = lab_name.strip()

    if lab_name.endswith(area):
        return lab_name

    return f"{lab_name} {area}"


def receive_location(lab_name: str | None):
    return lab_location(lab_name, "收樣區")


def experiment_temp_location(lab_name: str | None):
    return lab_location(lab_name, "實驗暫存區")


def pickup_location(lab_name: str | None):
    return lab_location(lab_name, "待取件區")


async def get_real_labs(db: AsyncSession):
    result = await db.execute(
        text(
            """
            SELECT
                id,
                code,
                name,
                capacity,
                is_active,
                created_at,
                updated_at
            FROM labs
            WHERE is_active = TRUE
            ORDER BY code ASC
            """
        )
    )

    return [row_to_dict(row) for row in result]


async def get_generated_storage_locations(db: AsyncSession):
    labs = await get_real_labs(db)
    storage_locations = []

    for lab in labs:
        lab_id = lab.get("id")
        lab_code = lab.get("code")
        lab_name = lab.get("name")

        areas = [
            ("receive", "收樣區"),
            ("experiment-temp", "實驗暫存區"),
            ("pickup", "待取件區"),
        ]

        for area_code, area_name in areas:
            storage_locations.append(
                {
                    "id": f"{lab_id}-{area_code}",
                    "code": f"{lab_code}-{area_code.upper()}",
                    "name": lab_location(lab_name, area_name),
                    "lab_id": lab_id,
                    "lab_code": lab_code,
                    "lab_name": lab_name,
                    "area": area_name,
                    "is_active": True,
                }
            )

    return storage_locations


async def get_real_users(db: AsyncSession):
    """讀正式 users。

    優先支援 users.lab_id -> labs.id。
    如果你的 users table 沒有 lab_id，會 fallback 成 SELECT * FROM users。
    """

    try:
        result = await db.execute(
            text(
                """
                SELECT
                    u.id,
                    u.name,
                    u.email,
                    u.role,
                    u.department,
                    u.lab_id,
                    l.name AS lab_name,
                    l.code AS lab_code,
                    u.created_at,
                    u.updated_at
                FROM users u
                LEFT JOIN labs l
                    ON l.id = u.lab_id
                ORDER BY u.created_at DESC
                LIMIT 100
                """
            )
        )
        return [row_to_dict(row) for row in result]
    except Exception:
        await db.rollback()

        result = await db.execute(
            text(
                """
                SELECT *
                FROM users
                ORDER BY created_at DESC
                LIMIT 100
                """
            )
        )
        return [row_to_dict(row) for row in result]


async def get_real_orders(db: AsyncSession):
    result = await db.execute(
        text(
            """
            SELECT *
            FROM orders
            ORDER BY created_at DESC
            LIMIT 100
            """
        )
    )

    return [row_to_dict(row) for row in result]


async def get_real_order(db: AsyncSession, order_no_or_id: str):
    result = await db.execute(
        text(
            """
            SELECT *
            FROM orders
            WHERE CAST(id AS TEXT) = :order_no_or_id
               OR order_no = :order_no_or_id
            LIMIT 1
            """
        ),
        {"order_no_or_id": order_no_or_id},
    )

    row = result.fetchone()
    if row is None:
        return None

    return row_to_dict(row)


async def resolve_current_user(db: AsyncSession, request: Request | None = None):
    """用正式 users table 解析目前使用者。

    支援 header：
    - x-user-id
    - x-user-email
    - x-user-name

    如果沒有 header 或查不到 user，回傳一個安全 fallback，不再依賴 mock user。
    """

    user_id = None
    user_email = None
    user_name = None

    if request is not None:
        user_id = request.headers.get("x-user-id")
        user_email = request.headers.get("x-user-email")
        user_name = request.headers.get("x-user-name")

    try:
        if user_id or user_email:
            result = await db.execute(
                text(
                    """
                    SELECT
                        u.*,
                        l.name AS lab_name,
                        l.code AS lab_code
                    FROM users u
                    LEFT JOIN labs l
                        ON l.id = u.lab_id
                    WHERE (:user_id IS NOT NULL AND CAST(u.id AS TEXT) = :user_id)
                       OR (:user_email IS NOT NULL AND u.email = :user_email)
                    LIMIT 1
                    """
                ),
                {"user_id": user_id, "user_email": user_email},
            )

            row = result.fetchone()
            if row is not None:
                return row_to_dict(row)

        result = await db.execute(
            text(
                """
                SELECT
                    u.*,
                    l.name AS lab_name,
                    l.code AS lab_code
                FROM users u
                LEFT JOIN labs l
                    ON l.id = u.lab_id
                ORDER BY u.created_at DESC
                LIMIT 1
                """
            )
        )
        row = result.fetchone()
        if row is not None:
            return row_to_dict(row)

    except Exception:
        await db.rollback()

    return {
        "id": user_id or "system",
        "name": user_name or user_email or user_id or "系統",
        "email": user_email,
        "role": "system_admin",
        "role_name": "系統",
        "department": None,
        "lab_name": None,
        "lab_code": None,
    }


async def resolve_real_lab_name(db: AsyncSession, lab_value: str | None):
    """把 wip.lab_name 可能存的 lab id / code / name 轉成 labs.name。"""

    if not lab_value:
        return None

    result = await db.execute(
        text(
            """
            SELECT name
            FROM labs
            WHERE CAST(id AS TEXT) = :lab_value
               OR code = :lab_value
               OR name = :lab_value
            LIMIT 1
            """
        ),
        {"lab_value": lab_value},
    )

    row = result.fetchone()
    if row is None:
        # 為了不讓舊資料直接爆掉，查不到時先回傳原值。
        return lab_value

    return row._mapping["name"]


async def generate_sample_no(db: AsyncSession):
    result = await db.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM samples
            """
        )
    )
    total = int(result.fetchone()._mapping["total"])

    for index in range(total + 1, total + 1000):
        sample_no = f"SMP-2026-{index:04d}"

        exists_result = await db.execute(
            text(
                """
                SELECT 1
                FROM samples
                WHERE sample_no = :sample_no
                LIMIT 1
                """
            ),
            {"sample_no": sample_no},
        )
        exists = exists_result.fetchone()

        if exists is None:
            return sample_no

    raise HTTPException(status_code=500, detail="Unable to generate sample_no")


def normalize_lab_code_from_lab_code(lab_code: str | None):
    if not lab_code:
        return None

    cleaned = lab_code.strip().upper()

    if cleaned.startswith("LAB-") and len(cleaned) > 4:
        return cleaned.split("-", 1)[1]

    return cleaned


def normalize_lab_code(lab_name: str | None):
    if not lab_name:
        return "LAB"

    cleaned = lab_name.strip().replace(" ", "")
    lowered = cleaned.lower()

    if lowered.startswith("laba"):
        return "A"

    if lowered.startswith("labb"):
        return "B"

    if lowered.startswith("labc"):
        return "C"

    if lowered.startswith("labd"):
        return "D"

    chinese_lab_code_map = {
        "材料分析實驗室": "A",
        "電性測試實驗室": "B",
        "可靠度實驗室": "C",
    }

    return chinese_lab_code_map.get(cleaned, cleaned.upper())


async def resolve_lab_code(db: AsyncSession, lab_name: str | None):
    if not lab_name:
        return "LAB"

    lab_result = await db.execute(
        text(
            """
            SELECT code
            FROM labs
            WHERE name = :lab_name
               OR code = :lab_name
               OR CAST(id AS TEXT) = :lab_name
            LIMIT 1
            """
        ),
        {"lab_name": lab_name},
    )
    lab = lab_result.fetchone()

    if lab is not None:
        lab_code = normalize_lab_code_from_lab_code(lab._mapping["code"])
        if lab_code:
            return lab_code

    return normalize_lab_code(lab_name)


async def generate_unique_wip_no(
    db: AsyncSession,
    sample_no: str,
    index: int,
    lab_name: str | None = None,
):
    base_no = sample_no.replace("SMP-", "WIP-")
    lab_code = await resolve_lab_code(db, lab_name)

    for offset in range(index, index + 1000):
        wip_no = f"{base_no}-{lab_code}-{offset:02d}"

        exists_result = await db.execute(
            text(
                """
                SELECT 1
                FROM wips
                WHERE wip_no = :wip_no
                LIMIT 1
                """
            ),
            {"wip_no": wip_no},
        )
        exists = exists_result.fetchone()

        if exists is None:
            return wip_no

    raise HTTPException(status_code=500, detail="Unable to generate unique_wip_no")


def safe_json_loads(value: Any):
    if value is None:
        return None

    if isinstance(value, (dict, list)):
        return value

    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None

        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None

    return None


def normalize_requested_experiments(value: Any):
    parsed = safe_json_loads(value)

    if isinstance(parsed, list):
        result = []
        for item in parsed:
            if not isinstance(item, dict):
                continue

            lab_name = item.get("lab_name") or item.get("lab") or item.get("target_lab")
            experiment_item = (
                item.get("experiment_item")
                or item.get("test_item")
                or item.get("item")
                or item.get("name")
            )

            if lab_name and experiment_item:
                result.append(
                    {
                        "lab_name": str(lab_name).strip(),
                        "experiment_item": str(experiment_item).strip(),
                    }
                )

        return result

    return []


def parse_requested_experiments_from_sample(sample: dict):
    # 實驗需求統一從 samples.experiment_item 解析。
    # 格式例如：材料分析實驗室:SEM 觀察、電性測試實驗室:光學量測
    experiment_item = sample.get("experiment_item") or ""
    result = []

    for part in experiment_item.split("、"):
        part = part.strip()

        if ":" not in part:
            continue

        lab_name, item_name = part.split(":", 1)

        if lab_name.strip() and item_name.strip():
            result.append(
                {
                    "lab_name": lab_name.strip(),
                    "experiment_item": item_name.strip(),
                }
            )

    return result


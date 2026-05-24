"""Transfers helper/service layer.

這個檔案由原本過長的 route 檔拆出，集中放置權限判斷、位置轉換、ID 產生、資料查詢等輔助邏輯。
Route 檔應只保留 HTTP endpoint，避免 API 入口與流程邏輯混在一起。
"""

from uuid import UUID

from fastapi import HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


fallback_user = {
    "id": "system",
    "name": "系統",
    "role": "system_admin",
    "role_name": "系統管理者",
    "department": None,
    "lab_name": None,
    "email": "",
}


async def get_active_user(
    db: AsyncSession,
    request: Request | None = None,
):
    """讀正式目前使用者；不再依賴 mock user。

    注意：這是 async function，route 端一定要用 await。
    """
    try:
        from app.services.temporary_others_service import resolve_current_user

        return await resolve_current_user(db, request)
    except Exception:
        await db.rollback()
        return fallback_user


def get_user_lab(user: dict):
    return user.get("lab_name") or user.get("department")


def lab_location(lab_name: str | None, area: str):
    if not lab_name:
        return area

    lab_name = lab_name.strip()

    if lab_name.endswith(area):
        return lab_name

    return f"{lab_name} {area}"


def receive_location(lab_name: str | None):
    return lab_location(lab_name, "收樣區")


def transfer_waiting_location(lab_name: str | None):
    return lab_location(lab_name, "交接待送區")


def build_transfer_visibility_filter(current_user: dict):
    role = current_user.get("role")
    where_clauses = []
    params = {}

    if role == "system_admin":
        return where_clauses, params

    if role in ("lab_engineer", "lab_supervisor"):
        current_lab = get_user_lab(current_user)

        if not current_lab:
            where_clauses.append("1 = 0")
            return where_clauses, params

        # Lab 使用者要同時看得到：
        # 1. 自己 Lab 交出去的交接單
        # 2. 別人 Lab 交給自己 Lab 的待接收交接單
        where_clauses.append("(from_lab = :current_lab OR to_lab = :current_lab)")
        params["current_lab"] = current_lab
        return where_clauses, params

    if role == "plant_user":
        where_clauses.append("1 = 0")
        return where_clauses, params

    where_clauses.append("1 = 0")
    return where_clauses, params


def validate_uuid(value: str | None, field_name: str) -> None:
    try:
        UUID(str(value))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must be a valid UUID",
        )


async def generate_transfer_no(db: AsyncSession):
    result = await db.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM transfers
            """
        )
    )

    total = int(result.fetchone()._mapping["total"])

    for index in range(total + 1, total + 1000):
        transfer_no = f"TRF-2026-{index:04d}"

        exists_result = await db.execute(
            text(
                """
                SELECT 1
                FROM transfers
                WHERE transfer_no = :transfer_no
                LIMIT 1
                """
            ),
            {"transfer_no": transfer_no},
        )
        exists = exists_result.fetchone()

        if exists is None:
            return transfer_no

    raise HTTPException(status_code=500, detail="Unable to generate transfer_no")


async def create_pending_sample_transfer_if_missing(
    db: AsyncSession,
    sample: dict,
    from_lab: str,
    to_lab: str,
    handed_by: str | None,
    note: str | None = None,
) -> dict | None:
    existing_result = await db.execute(
        text(
            """
            SELECT *
            FROM transfers
            WHERE target_type = 'sample'
              AND target_id = :sample_id
              AND from_lab = :from_lab
              AND to_lab = :to_lab
              AND status = 'pending'
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {
            "sample_id": sample["id"],
            "from_lab": from_lab,
            "to_lab": to_lab,
        },
    )
    existing = existing_result.fetchone()
    if existing is not None:
        return dict(existing._mapping)

    result = await db.execute(
        text(
            """
            INSERT INTO transfers (
                transfer_no,
                target_type,
                target_id,
                order_no,
                sample_no,
                from_lab,
                to_lab,
                handed_by,
                status,
                note
            )
            VALUES (
                :transfer_no,
                'sample',
                :sample_id,
                :order_no,
                :sample_no,
                :from_lab,
                :to_lab,
                :handed_by,
                'pending',
                :note
            )
            RETURNING *
            """
        ),
        {
            "transfer_no": await generate_transfer_no(db),
            "sample_id": sample["id"],
            "order_no": sample.get("order_no"),
            "sample_no": sample.get("sample_no"),
            "from_lab": from_lab,
            "to_lab": to_lab,
            "handed_by": handed_by,
            "note": note,
        },
    )
    created = result.fetchone()
    return dict(created._mapping) if created is not None else None


async def get_transfer_or_404(transfer_id: str, db: AsyncSession):
    validate_uuid(transfer_id, "transfer_id")

    result = await db.execute(
        text(
            """
            SELECT *
            FROM transfers
            WHERE id = :transfer_id
            """
        ),
        {"transfer_id": transfer_id},
    )

    transfer = result.fetchone()

    if transfer is None:
        raise HTTPException(status_code=404, detail="Transfer not found")

    return dict(transfer._mapping)


async def get_sample_or_404(sample_id: str, db: AsyncSession):
    validate_uuid(sample_id, "sample_id")

    result = await db.execute(
        text(
            """
            SELECT *
            FROM samples
            WHERE id = :sample_id
            """
        ),
        {"sample_id": sample_id},
    )

    sample = result.fetchone()

    if sample is None:
        raise HTTPException(status_code=404, detail="Sample not found")

    return dict(sample._mapping)


async def get_wip_or_404(wip_id: str, db: AsyncSession):
    validate_uuid(wip_id, "wip_id")

    result = await db.execute(
        text(
            """
            SELECT *
            FROM wips
            WHERE id = :wip_id
            """
        ),
        {"wip_id": wip_id},
    )

    wip = result.fetchone()

    if wip is None:
        raise HTTPException(status_code=404, detail="WIP not found")

    return dict(wip._mapping)


async def update_next_lab_wips_location(
    db: AsyncSession,
    sample_id: str,
    to_lab: str | None,
    next_location: str,
):
    if not to_lab:
        return

    await db.execute(
        text(
            """
            UPDATE wips
            SET
                current_location = :next_location,
                updated_at = NOW()
            WHERE sample_id = :sample_id
              AND lab_name = :to_lab
              AND status <> 'completed'
            """
        ),
        {
            "sample_id": sample_id,
            "to_lab": to_lab,
            "next_location": next_location,
        },
    )

"""Transfers helper/service layer.

這個檔案由原本過長的 route 檔拆出，集中放置權限判斷、位置轉換、ID 產生、資料查詢等輔助邏輯。
Route 檔應只保留 HTTP endpoint，避免 API 入口與流程邏輯混在一起。
"""

from uuid import UUID

from fastapi import Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db


fallback_user = {
    "id": "fallback",
    "name": "張志明",
    "role": "lab_staff",
    "role_name": "實驗室人員",
    "department": "Lab A",
    "lab_name": "Lab A",
    "email": "",
}


def get_active_user(request: Request | None = None):
    try:
        # TODO(integration): 目前暫時從 app.routes.others 取得使用者。
        # 正式整合 role.md 後，請改接 GET /api/me 或正式 auth/user service。
        from app.routes.others import resolve_current_user

        # 這裡保留舊行為，避免前端在正式 role API 上線前無法取得登入身分。
        return resolve_current_user(request)
    except Exception:
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

    if role in ("lab_staff", "lab_supervisor"):
        current_lab = get_user_lab(current_user)

        if not current_lab:
            where_clauses.append("1 = 0")
            return where_clauses, params

        where_clauses.append("from_lab = :current_lab")
        params["current_lab"] = current_lab
        return where_clauses, params

    if role == "factory_user":
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


def generate_transfer_no(db: Session):
    result = db.execute(
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

        exists = db.execute(
            text(
                """
                SELECT 1
                FROM transfers
                WHERE transfer_no = :transfer_no
                LIMIT 1
                """
            ),
            {"transfer_no": transfer_no},
        ).fetchone()

        if exists is None:
            return transfer_no

    raise HTTPException(status_code=500, detail="Unable to generate transfer_no")


def get_transfer_or_404(transfer_id: str, db: Session):
    validate_uuid(transfer_id, "transfer_id")

    result = db.execute(
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


def get_sample_or_404(sample_id: str, db: Session):
    validate_uuid(sample_id, "sample_id")

    result = db.execute(
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


def get_wip_or_404(wip_id: str, db: Session):
    validate_uuid(wip_id, "wip_id")

    result = db.execute(
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


def update_next_lab_wips_location(
    db: Session,
    sample_id: str,
    to_lab: str | None,
    next_location: str,
):
    if not to_lab:
        return

    db.execute(
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

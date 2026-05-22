"""WIPs helper/service layer.

這個檔案由原本過長的 route 檔拆出，集中放置權限判斷、位置轉換、ID 產生、資料查詢等輔助邏輯。
Route 檔應只保留 HTTP endpoint，避免 API 入口與流程邏輯混在一起。
"""

from uuid import UUID

from fastapi import Depends, HTTPException, Query, Request
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


def experiment_temp_location(lab_name: str | None):
    return lab_location(lab_name, "實驗暫存區")


def machine_location(lab_name: str | None):
    return lab_location(lab_name, "機台區")


def build_wip_visibility_filter(current_user: dict):
    role = current_user.get("role")
    where_clauses = []
    params = {}

    if role == "system_admin":
        return where_clauses, params

    if role == "factory_user":
        where_clauses.append("s.applicant_name = :applicant_name")
        params["applicant_name"] = current_user.get("name")
        return where_clauses, params

    if role in ("lab_staff", "lab_supervisor"):
        current_lab = get_user_lab(current_user)

        if not current_lab:
            where_clauses.append("1 = 0")
            return where_clauses, params

        # WIP 以樣品實體位置判斷目前在哪個 Lab。
        where_clauses.append("w.current_location LIKE :current_lab_prefix")
        params["current_lab_prefix"] = f"{current_lab}%"
        return where_clauses, params

    where_clauses.append("1 = 0")
    return where_clauses, params


def can_view_wip(current_user: dict, wip: dict, sample: dict | None = None) -> bool:
    role = current_user.get("role")

    if role == "system_admin":
        return True

    if role == "factory_user":
        return bool(sample and sample.get("applicant_name") == current_user.get("name"))

    if role in ("lab_staff", "lab_supervisor"):
        current_lab = get_user_lab(current_user)
        current_location = wip.get("current_location") or ""
        return bool(current_lab and current_location.startswith(current_lab))

    return False


def can_manage_wip(current_user: dict, wip: dict) -> bool:
    role = current_user.get("role")

    if role == "system_admin":
        return True

    if role not in ("lab_staff", "lab_supervisor"):
        return False

    current_lab = get_user_lab(current_user)
    current_location = wip.get("current_location") or ""
    return bool(current_lab and current_location.startswith(current_lab))


def validate_uuid(value: str | None, field_name: str) -> None:
    try:
        UUID(str(value))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must be a valid UUID",
        )


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


def get_sample_by_id(sample_id: str, db: Session):
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
        return None

    return dict(sample._mapping)

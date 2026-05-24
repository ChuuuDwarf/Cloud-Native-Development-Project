"""WIPs helper/service layer.

這個檔案集中放置 WIP 權限判斷、位置轉換、ID 驗證、資料查詢等輔助邏輯。
重點：
- WIP 的可見範圍用 w.lab_name 判斷，不能用 current_location。
- current_location 只代表樣品 / WIP 目前所在位置，不代表 WIP 原本歸屬哪個 Lab。
"""

from uuid import UUID

from fastapi import HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session


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

    if role in ("system_admin", "lab_supervisor"):
        return where_clauses, params

    if role == "factory_user":
        where_clauses.append("s.applicant_name = :applicant_name")
        params["applicant_name"] = current_user.get("name")
        return where_clauses, params

    if role == "lab_staff":
        current_lab = get_user_lab(current_user)

        if not current_lab:
            where_clauses.append("1 = 0")
            return where_clauses, params

        params["current_lab"] = current_lab

        where_clauses.append(
            """
            (
                w.lab_name = :current_lab
                OR EXISTS (
                    SELECT 1
                    FROM transfers t
                    WHERE t.target_type = 'sample'
                      AND t.target_id = w.sample_id
                      AND t.to_lab = :current_lab
                )
            )
            """
        )

        return where_clauses, params

    where_clauses.append("1 = 0")
    return where_clauses, params

def can_view_wip(
    current_user: dict,
    wip: dict,
    sample: dict | None = None,
    db: Session | None = None,
) -> bool:
    role = current_user.get("role")

    if role in ("system_admin", "lab_supervisor"):
        return True

    if role == "factory_user":
        return bool(sample and sample.get("applicant_name") == current_user.get("name"))

    if role == "lab_staff":
        current_lab = get_user_lab(current_user)

        if not current_lab:
            return False

        if wip.get("lab_name") == current_lab:
            return True

        if db is None:
            return False

        related = db.execute(
            text(
                """
                SELECT 1
                FROM transfers t
                WHERE t.target_type = 'sample'
                  AND t.target_id = :sample_id
                  AND t.to_lab = :current_lab
                LIMIT 1
                """
            ),
            {
                "sample_id": wip.get("sample_id"),
                "current_lab": current_lab,
            },
        ).fetchone()

        return related is not None

    return False

def can_manage_wip(current_user: dict, wip: dict) -> bool:
    role = current_user.get("role")

    if role == "system_admin":
        return True

    if role not in ("lab_staff", "lab_supervisor"):
        return False

    current_lab = get_user_lab(current_user)

    # 操作 WIP 也以 WIP 歸屬 Lab 為準，避免 current_location 被更新成
    # 「已由使用者取回」後，原 Lab 連自己的 WIP 都不能操作 / 補資料。
    return bool(current_lab and wip.get("lab_name") == current_lab)


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
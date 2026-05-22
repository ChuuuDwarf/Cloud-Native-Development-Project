"""Samples helper/service layer.

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


def get_lab_from_location(location: str | None):
    if not location:
        return None

    location = location.strip()

    if location.startswith("Lab A"):
        return "Lab A"

    if location.startswith("Lab B"):
        return "Lab B"

    if location.startswith("Lab C"):
        return "Lab C"

    if location.startswith("Lab D"):
        return "Lab D"

    return None


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


def machine_location(lab_name: str | None):
    return lab_location(lab_name, "機台區")


def transfer_waiting_location(lab_name: str | None):
    return lab_location(lab_name, "交接待送區")


def pickup_location(lab_name: str | None):
    return lab_location(lab_name, "待取件區")


def normalize_location_for_action(
    payload_location: str | None,
    current_lab: str | None,
    default_area: str,
):
    if payload_location:
        return payload_location

    return lab_location(current_lab, default_area)


def build_sample_visibility_filter(current_user: dict, scope: str | None = None):
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

        params["current_lab"] = current_lab
        params["current_lab_prefix"] = f"{current_lab}%"

        if scope == "all":
            where_clauses.append(
                """
                (
                    s.current_location LIKE :current_lab_prefix
                    OR EXISTS (
                        SELECT 1
                        FROM wips w
                        WHERE w.sample_id = s.id
                          AND w.lab_name = :current_lab
                    )
                    OR EXISTS (
                        SELECT 1
                        FROM transfers t
                        WHERE t.target_type = 'sample'
                          AND t.target_id = s.id
                          AND (
                              t.from_lab = :current_lab
                              OR t.to_lab = :current_lab
                          )
                    )
                )
                """
            )
            return where_clauses, params

        where_clauses.append("s.current_location LIKE :current_lab_prefix")
        return where_clauses, params

    where_clauses.append("1 = 0")
    return where_clauses, params


def can_view_sample(current_user: dict, sample: dict, db: Session | None = None) -> bool:
    role = current_user.get("role")

    if role == "system_admin":
        return True

    if role == "factory_user":
        return sample.get("applicant_name") == current_user.get("name")

    if role in ("lab_staff", "lab_supervisor"):
        current_lab = get_user_lab(current_user)
        current_location = sample.get("current_location") or ""

        if current_lab and current_location.startswith(current_lab):
            return True

        if db is None or not current_lab:
            return False

        related = db.execute(
            text(
                """
                SELECT 1
                WHERE EXISTS (
                    SELECT 1
                    FROM wips
                    WHERE sample_id = :sample_id
                      AND lab_name = :current_lab
                )
                OR EXISTS (
                    SELECT 1
                    FROM transfers
                    WHERE target_type = 'sample'
                      AND target_id = :sample_id
                      AND (
                          from_lab = :current_lab
                          OR to_lab = :current_lab
                      )
                )
                LIMIT 1
                """
            ),
            {
                "sample_id": sample.get("id"),
                "current_lab": current_lab,
            },
        ).fetchone()

        return related is not None

    return False


def can_manage_sample(current_user: dict, sample: dict) -> bool:
    role = current_user.get("role")

    if role == "system_admin":
        return True

    if role not in ("lab_staff", "lab_supervisor"):
        return False

    current_lab = get_user_lab(current_user)
    current_location = sample.get("current_location") or ""

    return bool(current_lab and current_location.startswith(current_lab))


def can_confirm_pickup(current_user: dict, sample: dict) -> bool:
    return (
        current_user.get("role") == "factory_user"
        and sample.get("applicant_name") == current_user.get("name")
        and sample.get("status") == "outbound"
    )


def validate_uuid(value: str | None, field_name: str) -> None:
    try:
        UUID(str(value))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must be a valid UUID",
        )


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


def update_current_lab_wips_location(
    db: Session,
    sample_id: str,
    current_lab: str | None,
    next_location: str,
):
    if not current_lab:
        return

    db.execute(
        text(
            """
            UPDATE wips
            SET
                current_location = :next_location,
                updated_at = NOW()
            WHERE sample_id = :sample_id
              AND lab_name = :current_lab
              AND status <> 'completed'
            """
        ),
        {
            "sample_id": sample_id,
            "current_lab": current_lab,
            "next_location": next_location,
        },
    )


def update_all_wips_location(
    db: Session,
    sample_id: str,
    next_location: str,
):
    db.execute(
        text(
            """
            UPDATE wips
            SET
                current_location = :next_location,
                updated_at = NOW()
            WHERE sample_id = :sample_id
            """
        ),
        {
            "sample_id": sample_id,
            "next_location": next_location,
        },
    )


def normalize_lab_code(lab_name: str | None):
    if not lab_name:
        return "LAB"

    cleaned = lab_name.strip().replace(" ", "")

    if cleaned.lower().startswith("laba"):
        return "A"

    if cleaned.lower().startswith("labb"):
        return "B"

    if cleaned.lower().startswith("labc"):
        return "C"

    if cleaned.lower().startswith("labd"):
        return "D"

    return cleaned.upper()


def generate_unique_wip_no(
    db: Session,
    sample: dict,
    lab_name: str | None,
    preferred_wip_no: str | None = None,
):
    if preferred_wip_no:
        exists = db.execute(
            text(
                """
                SELECT 1
                FROM wips
                WHERE wip_no = :wip_no
                LIMIT 1
                """
            ),
            {"wip_no": preferred_wip_no},
        ).fetchone()

        if exists is None:
            return preferred_wip_no

    sample_no = sample.get("sample_no") or "SMP"
    lab_code = normalize_lab_code(lab_name)

    base_no = sample_no.replace("SMP-", "WIP-")

    for index in range(1, 1000):
        candidate = f"{base_no}-{lab_code}-{index:02d}"

        exists = db.execute(
            text(
                """
                SELECT 1
                FROM wips
                WHERE wip_no = :wip_no
                LIMIT 1
                """
            ),
            {"wip_no": candidate},
        ).fetchone()

        if exists is None:
            return candidate

    raise HTTPException(
        status_code=500,
        detail="Unable to generate unique WIP number",
    )

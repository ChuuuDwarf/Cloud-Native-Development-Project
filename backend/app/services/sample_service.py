"""Samples helper/service layer.

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
    """讀正式目前使用者；不再依賴 mock user。"""
    try:
        from app.services.temporary_others_service import resolve_current_user

        return await resolve_current_user(db, request)
    except Exception:
        await db.rollback()
        return fallback_user


def get_user_lab(user: dict):
    return user.get("lab_name") or user.get("department")


def get_lab_from_location(location: str | None):
    """從位置字串推回 lab 名稱。

    以前只支援 Lab A/B/C，現在改成支援正式 lab name：
    例如「材料分析實驗室 實驗暫存區」=>「材料分析實驗室」。
    """
    if not location:
        return None

    location = location.strip()
    area_suffixes = [
        "收樣區",
        "實驗暫存區",
        "機台區",
        "交接待送區",
        "待取件區",
    ]

    for area in area_suffixes:
        suffix = f" {area}"
        if location.endswith(suffix):
            return location[: -len(suffix)].strip() or None

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


def is_factory_role(role: str | None) -> bool:
    return role == "plant_user"


def is_lab_role(role: str | None) -> bool:
    return role in ("lab_engineer", "lab_supervisor")


def build_sample_visibility_filter(current_user: dict, scope: str | None = None):
    role = current_user.get("role")
    where_clauses = []
    params = {}

    if role == "system_admin":
        return where_clauses, params

    if is_factory_role(role):
        where_clauses.append("s.applicant_name = :applicant_name")
        params["applicant_name"] = current_user.get("name")
        return where_clauses, params

    if role == "lab_supervisor":
        current_lab = get_user_lab(current_user)

        if not current_lab:
            where_clauses.append("1 = 0")
            return where_clauses, params

        params["current_lab"] = current_lab
        params["current_lab_prefix"] = f"{current_lab}%"

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

    if role == "lab_engineer":
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

async def can_view_sample(current_user: dict, sample: dict, db: AsyncSession | None = None) -> bool:
    role = current_user.get("role")

    if role in ("system_admin", "lab_supervisor"):
        return True

    if is_factory_role(role):
        return sample.get("applicant_name") == current_user.get("name")

    if role == "lab_engineer":
        current_lab = get_user_lab(current_user)
        current_location = sample.get("current_location") or ""

        if current_lab and current_location.startswith(current_lab):
            return True

        if db is None or not current_lab:
            return False

        related_result = await db.execute(
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
        )
        related = related_result.fetchone()

        return related is not None

    return False

def can_manage_sample(current_user: dict, sample: dict) -> bool:
    role = current_user.get("role")

    if role == "system_admin":
        return True

    if not is_lab_role(role) and role != "system_admin":
        return False

    current_lab = get_user_lab(current_user)
    current_location = sample.get("current_location") or ""

    return bool(current_lab and current_location.startswith(current_lab))


def can_confirm_pickup(current_user: dict, sample: dict) -> bool:
    return (
        is_factory_role(current_user.get("role"))
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


async def update_current_lab_wips_location(
    db: AsyncSession,
    sample_id: str,
    current_lab: str | None,
    next_location: str,
):
    if not current_lab:
        return

    await db.execute(
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


async def update_all_wips_location(
    db: AsyncSession,
    sample_id: str,
    next_location: str,
):
    await db.execute(
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
    lowered = cleaned.lower()

    if lowered.startswith("laba"):
        return "A"

    if lowered.startswith("labb"):
        return "B"

    if lowered.startswith("labc"):
        return "C"

    if lowered.startswith("labd"):
        return "D"

    # 正式資料的 lab 通常是「材料分析實驗室」這類中文名稱；
    # 若無法查到 labs.code，就用固定對照避免 WIP 編號塞整個實驗室名稱。
    chinese_lab_code_map = {
        "材料分析實驗室": "A",
        "電性測試實驗室": "B",
        "可靠度實驗室": "C",
    }

    return chinese_lab_code_map.get(cleaned, cleaned.upper())


def normalize_lab_code_from_lab_code(lab_code: str | None):
    if not lab_code:
        return None

    cleaned = lab_code.strip().upper()

    if cleaned.startswith("LAB-") and len(cleaned) > 4:
        return cleaned.split("-", 1)[1]

    return cleaned


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
    sample: dict,
    lab_name: str | None,
    preferred_wip_no: str | None = None,
):
    # WIP 編號統一由後端產生，避免前端舊格式造成：
    # WIP-2026-0003-01
    # WIP-2026-0003-A-01
    # 兩種格式混在一起。
    #
    # 統一格式：
    # WIP-YYYY-NNNN-{LabCode}-XX
    #
    # 例如：
    # SMP-2026-0003 + Lab A => WIP-2026-0003-A-01
    # SMP-2026-0003 + Lab B => WIP-2026-0003-B-01

    sample_no = sample.get("sample_no") or "SMP"
    lab_code = await resolve_lab_code(db, lab_name)

    base_no = sample_no.replace("SMP-", "WIP-")

    for index in range(1, 1000):
        candidate = f"{base_no}-{lab_code}-{index:02d}"

        exists_result = await db.execute(
            text(
                """
                SELECT 1
                FROM wips
                WHERE wip_no = :wip_no
                LIMIT 1
                """
            ),
            {"wip_no": candidate},
        )
        exists = exists_result.fetchone()

        if exists is None:
            return candidate

    raise HTTPException(
        status_code=500,
        detail="Unable to generate unique WIP number",
    )

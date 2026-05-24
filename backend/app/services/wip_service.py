"""WIPs helper/service layer.

這個檔案集中放置 WIP 權限判斷、位置轉換、ID 驗證、資料查詢等輔助邏輯。
重點：
- WIP 的可見範圍用 w.lab_name 判斷，不能用 current_location。
- current_location 只代表樣品 / WIP 目前所在位置，不代表 WIP 原本歸屬哪個 Lab。
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


def is_factory_role(role: str | None) -> bool:
    return role == "plant_user"


def is_lab_role(role: str | None) -> bool:
    return role in ("lab_engineer", "lab_supervisor")


def build_wip_visibility_filter(current_user: dict):
    role = current_user.get("role")
    where_clauses = []
    params = {}

    if role in ("system_admin", "lab_supervisor"):
        return where_clauses, params

    if is_factory_role(role):
        where_clauses.append("s.applicant_name = :applicant_name")
        params["applicant_name"] = current_user.get("name")
        return where_clauses, params

    if is_lab_role(role):
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

async def can_view_wip(
    current_user: dict,
    wip: dict,
    sample: dict | None = None,
    db: AsyncSession | None = None,
) -> bool:
    role = current_user.get("role")

    if role in ("system_admin", "lab_supervisor"):
        return True

    if is_factory_role(role):
        return bool(sample and sample.get("applicant_name") == current_user.get("name"))

    if is_lab_role(role):
        current_lab = get_user_lab(current_user)

        if not current_lab:
            return False

        if wip.get("lab_name") == current_lab:
            return True

        if db is None:
            return False

        related_result = await db.execute(
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
        )
        related = related_result.fetchone()

        return related is not None

    return False

def can_manage_wip(current_user: dict, wip: dict) -> bool:
    role = current_user.get("role")

    if role == "system_admin":
        return True

    if not is_lab_role(role):
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


async def get_sample_by_id(sample_id: str, db: AsyncSession):
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
        return None

    return dict(sample._mapping)


def parse_requested_experiments(experiment_item: str | None) -> list[dict[str, str]]:
    if not experiment_item:
        return []

    experiments: list[dict[str, str]] = []

    for part in experiment_item.split("、"):
        part = part.strip()

        if ":" not in part:
            continue

        lab_name, item_name = part.split(":", 1)
        lab_name = lab_name.strip()
        item_name = item_name.strip()

        if lab_name and item_name:
            experiments.append({"lab_name": lab_name, "experiment_item": item_name})

    return experiments


def normalize_flow_value(value: str | None) -> str:
    return (value or "").strip().lower()


def find_current_experiment_index(
    experiments: list[dict[str, str]],
    wip: dict,
) -> int | None:
    wip_lab = normalize_flow_value(wip.get("lab_name"))
    wip_experiment = normalize_flow_value(wip.get("experiment_item"))

    for index, experiment in enumerate(experiments):
        if (
            normalize_flow_value(experiment.get("lab_name")) == wip_lab
            and normalize_flow_value(experiment.get("experiment_item")) == wip_experiment
        ):
            return index

    return None


async def complete_wip_sample_flow(
    db: AsyncSession,
    wip: dict,
    current_lab: str | None,
    operator_name: str,
) -> None:
    if not current_lab:
        return

    sample = await get_sample_by_id(wip.get("sample_id"), db)
    if sample is None:
        return

    experiments = parse_requested_experiments(sample.get("experiment_item"))
    current_index = find_current_experiment_index(experiments, wip)
    current_lab_temp_location = experiment_temp_location(current_lab)

    if current_index is None:
        await db.execute(
            text(
                """
                UPDATE samples
                SET
                    status = 'split',
                    current_location = :current_location,
                    updated_at = NOW()
                WHERE id = :sample_id
                """
            ),
            {
                "sample_id": sample["id"],
                "current_location": current_lab_temp_location,
            },
        )
        return

    next_experiment = (
        experiments[current_index + 1]
        if current_index + 1 < len(experiments)
        else None
    )

    if next_experiment is None:
        await db.execute(
            text(
                """
                UPDATE samples
                SET
                    status = 'split',
                    current_location = :current_location,
                    updated_at = NOW()
                WHERE id = :sample_id
                """
            ),
            {
                "sample_id": sample["id"],
                "current_location": current_lab_temp_location,
            },
        )
        await db.execute(
            text(
                """
                INSERT INTO sample_histories (
                    sample_id,
                    action,
                    from_status,
                    to_status,
                    description,
                    operator_name,
                    lab_name
                )
                VALUES (
                    :sample_id,
                    'wip_completed_ready_to_notify_pickup',
                    :from_status,
                    'split',
                    :description,
                    :operator_name,
                    :lab_name
                )
                """
            ),
            {
                "sample_id": sample["id"],
                "from_status": sample.get("status"),
                "description": f"{current_lab} 完成 {wip.get('experiment_item')}，可通知使用者取件",
                "operator_name": operator_name,
                "lab_name": current_lab,
            },
        )
        return

    next_lab = next_experiment["lab_name"]
    if normalize_flow_value(next_lab) == normalize_flow_value(current_lab):
        await db.execute(
            text(
                """
                UPDATE samples
                SET
                    status = 'split',
                    current_location = :current_location,
                    updated_at = NOW()
                WHERE id = :sample_id
                """
            ),
            {
                "sample_id": sample["id"],
                "current_location": current_lab_temp_location,
            },
        )
        return

    await db.execute(
        text(
            """
            UPDATE samples
            SET
                status = 'pending_transfer',
                current_location = :current_location,
                updated_at = NOW()
            WHERE id = :sample_id
            """
        ),
        {
            "sample_id": sample["id"],
            "current_location": current_lab_temp_location,
        },
    )

    note = f"{current_lab} 完成 {wip.get('experiment_item')}，可交接至 {next_lab}"

    await db.execute(
        text(
            """
            INSERT INTO sample_histories (
                sample_id,
                action,
                from_status,
                to_status,
                description,
                operator_name,
                lab_name
            )
            VALUES (
                :sample_id,
                'wip_completed_pending_transfer',
                :from_status,
                'pending_transfer',
                :description,
                :operator_name,
                :lab_name
            )
            """
        ),
        {
            "sample_id": sample["id"],
            "from_status": sample.get("status"),
            "description": note,
            "operator_name": operator_name,
            "lab_name": current_lab,
        },
    )


async def update_sample_to_pending_transfer_if_ready(
    db: AsyncSession,
    sample_id: str,
    current_lab: str | None,
    next_location: str | None,
    operator_name: str,
) -> None:
    wips_result = await db.execute(
        text(
            """
            SELECT *
            FROM wips
            WHERE sample_id = :sample_id
              AND lab_name = :current_lab
              AND status = 'completed'
            ORDER BY completed_at IS NULL ASC, completed_at DESC, updated_at DESC
            LIMIT 1
            """
        ),
        {"sample_id": sample_id, "current_lab": current_lab},
    )
    completed_wip = wips_result.fetchone()
    if completed_wip is not None:
        await complete_wip_sample_flow(
            db=db,
            wip=dict(completed_wip._mapping),
            current_lab=current_lab,
            operator_name=operator_name,
        )

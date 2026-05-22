from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter(
    prefix="/api/samples",
    tags=["samples"],
)

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


def normalize_location_for_action(
    payload_location: str | None,
    current_lab: str | None,
    default_area: str,
):
    if payload_location:
        return payload_location

    return lab_location(current_lab, default_area)


def build_sample_visibility_filter(current_user: dict):
    role = current_user.get("role")
    where_clauses = []
    params = {}

    if role == "system_admin":
        return where_clauses, params

    if role == "factory_user":
        where_clauses.append("applicant_name = :applicant_name")
        params["applicant_name"] = current_user.get("name")
        return where_clauses, params

    if role in ("lab_staff", "lab_supervisor"):
        current_lab = get_user_lab(current_user)

        if not current_lab:
            where_clauses.append("1 = 0")
            return where_clauses, params

        where_clauses.append("current_location LIKE :current_lab_prefix")
        params["current_lab_prefix"] = f"{current_lab}%"
        return where_clauses, params

    where_clauses.append("1 = 0")
    return where_clauses, params


def can_view_sample(current_user: dict, sample: dict) -> bool:
    role = current_user.get("role")

    if role == "system_admin":
        return True

    if role == "factory_user":
        return sample.get("applicant_name") == current_user.get("name")

    if role in ("lab_staff", "lab_supervisor"):
        current_lab = get_user_lab(current_user)
        current_location = sample.get("current_location") or ""
        return bool(current_lab and current_location.startswith(current_lab))

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


@router.get("")
def get_samples(
    request: Request,
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    current_user = get_active_user(request)
    where_clauses, params = build_sample_visibility_filter(current_user)

    if status:
        where_clauses.append("status = :status")
        params["status"] = status

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    result = db.execute(
        text(
            f"""
            SELECT
                id,
                sample_no,
                order_no,
                sample_name,
                experiment_item,
                applicant_name,
                applicant_department,
                status,
                current_location,
                storage_location_id,
                received_at,
                received_by,
                picked_up_at,
                picked_up_by,
                note,
                created_at,
                updated_at
            FROM samples
            {where_sql}
            ORDER BY created_at DESC
            """
        ),
        params,
    )

    return [dict(row._mapping) for row in result]


@router.get("/{sample_id}")
def get_sample(
    sample_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    current_user = get_active_user(request)
    sample = get_sample_or_404(sample_id, db)

    if not can_view_sample(current_user, sample):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view this sample",
        )

    return sample


@router.get("/{sample_id}/history")
def get_sample_history(
    sample_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    current_user = get_active_user(request)
    sample = get_sample_or_404(sample_id, db)

    if not can_view_sample(current_user, sample):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view this sample",
        )

    result = db.execute(
        text(
            """
            SELECT
                id,
                sample_id,
                action,
                from_status,
                to_status,
                description,
                operator_name,
                created_at
            FROM sample_histories
            WHERE sample_id = :sample_id
            ORDER BY created_at DESC
            """
        ),
        {"sample_id": sample_id},
    )

    return [dict(row._mapping) for row in result]


@router.patch("/{sample_id}")
def update_sample(
    sample_id: str,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
):
    current_user = get_active_user(request)
    sample = get_sample_or_404(sample_id, db)

    if not can_manage_sample(current_user, sample):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to update this sample",
        )

    result = db.execute(
        text(
            """
            UPDATE samples
            SET
                sample_name = COALESCE(:sample_name, sample_name),
                experiment_item = COALESCE(:experiment_item, experiment_item),
                current_location = COALESCE(:current_location, current_location),
                note = COALESCE(:note, note),
                updated_at = NOW()
            WHERE id = :sample_id
            RETURNING *
            """
        ),
        {
            "sample_id": sample_id,
            "sample_name": payload.get("sample_name"),
            "experiment_item": payload.get("experiment_item"),
            "current_location": payload.get("current_location"),
            "note": payload.get("note"),
        },
    )

    db.commit()

    return dict(result.fetchone()._mapping)


@router.post("/{sample_id}/actions")
def sample_action(
    sample_id: str,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
):
    sample = get_sample_or_404(sample_id, db)
    current_user = get_active_user(request)
    current_lab = get_user_lab(current_user)
    action = payload.get("action")

    if action not in (
        "receive",
        "inbound",
        "outbound",
        "pickup_confirmed",
        "split",
    ):
        raise HTTPException(
            status_code=400,
            detail="action must be one of: receive, inbound, outbound, pickup_confirmed, split",
        )

    can_operate = can_manage_sample(current_user, sample)
    can_pickup = action == "pickup_confirmed" and can_confirm_pickup(current_user, sample)

    if not can_operate and not can_pickup:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to operate this sample",
        )

    if current_user.get("role") == "factory_user" and action != "pickup_confirmed":
        raise HTTPException(
            status_code=403,
            detail="廠區使用者只能在待取件狀態確認取件",
        )

    operator_name = payload.get("operator_name") or current_user.get("name")

    if not operator_name:
        raise HTTPException(
            status_code=400,
            detail="operator_name is required",
        )

    if action == "receive":
        if sample["status"] not in ("pending_receive", "transferring"):
            raise HTTPException(
                status_code=400,
                detail="只有待收樣或交接中的樣品可以確認收樣",
            )

        next_location = normalize_location_for_action(
            payload.get("current_location"),
            current_lab,
            "實驗暫存區",
        )

        result = db.execute(
            text(
                """
                UPDATE samples
                SET
                    status = 'received',
                    current_location = :next_location,
                    received_at = NOW(),
                    received_by = :operator_name,
                    updated_at = NOW()
                WHERE id = :sample_id
                RETURNING *
                """
            ),
            {
                "sample_id": sample_id,
                "next_location": next_location,
                "operator_name": operator_name,
            },
        )

        update_current_lab_wips_location(
            db=db,
            sample_id=sample_id,
            current_lab=current_lab,
            next_location=next_location,
        )

        db.execute(
            text(
                """
                UPDATE transfers
                SET
                    status = 'received',
                    received_by = :operator_name,
                    received_at = NOW(),
                    updated_at = NOW()
                WHERE target_type = 'sample'
                  AND target_id = :sample_id
                  AND to_lab = :current_lab
                  AND status = 'transferring'
                """
            ),
            {
                "sample_id": sample_id,
                "current_lab": current_lab,
                "operator_name": operator_name,
            },
        )

        db.execute(
            text(
                """
                INSERT INTO sample_histories (
                    sample_id,
                    action,
                    from_status,
                    to_status,
                    description,
                    operator_name
                )
                VALUES (
                    :sample_id,
                    'receive',
                    :from_status,
                    'received',
                    :description,
                    :operator_name
                )
                """
            ),
            {
                "sample_id": sample_id,
                "from_status": sample["status"],
                "description": f"確認收樣，樣品移至 {next_location}",
                "operator_name": operator_name,
            },
        )

        db.commit()

        return dict(result.fetchone()._mapping)

    if action == "inbound":
        storage_location_id = payload.get("storage_location_id")

        if storage_location_id:
            validate_uuid(storage_location_id, "storage_location_id")

        result = db.execute(
            text(
                """
                UPDATE samples
                SET
                    status = 'in_storage',
                    current_location = COALESCE(:current_location, current_location),
                    storage_location_id = COALESCE(:storage_location_id, storage_location_id),
                    updated_at = NOW()
                WHERE id = :sample_id
                RETURNING *
                """
            ),
            {
                "sample_id": sample_id,
                "current_location": payload.get("current_location"),
                "storage_location_id": storage_location_id,
            },
        )

        db.execute(
            text(
                """
                INSERT INTO sample_histories (
                    sample_id,
                    action,
                    from_status,
                    to_status,
                    description,
                    operator_name
                )
                VALUES (
                    :sample_id,
                    'inbound',
                    :from_status,
                    'in_storage',
                    '樣品入庫',
                    :operator_name
                )
                """
            ),
            {
                "sample_id": sample_id,
                "from_status": sample["status"],
                "operator_name": operator_name,
            },
        )

        db.commit()

        return dict(result.fetchone()._mapping)

    if action == "outbound":
        next_location = normalize_location_for_action(
            payload.get("current_location"),
            current_lab,
            "待取件區",
        )

        result = db.execute(
            text(
                """
                UPDATE samples
                SET
                    status = 'outbound',
                    current_location = :next_location,
                    note = COALESCE(:note, note),
                    updated_at = NOW()
                WHERE id = :sample_id
                RETURNING *
                """
            ),
            {
                "sample_id": sample_id,
                "next_location": next_location,
                "note": payload.get("note"),
            },
        )

        update_all_wips_location(
            db=db,
            sample_id=sample_id,
            next_location=next_location,
        )

        db.execute(
            text(
                """
                INSERT INTO sample_histories (
                    sample_id,
                    action,
                    from_status,
                    to_status,
                    description,
                    operator_name
                )
                VALUES (
                    :sample_id,
                    'outbound',
                    :from_status,
                    'outbound',
                    :description,
                    :operator_name
                )
                """
            ),
            {
                "sample_id": sample_id,
                "from_status": sample["status"],
                "description": f"通知原使用者取件，樣品移至 {next_location}",
                "operator_name": operator_name,
            },
        )

        db.commit()

        return dict(result.fetchone()._mapping)

    if action == "pickup_confirmed":
        if sample["status"] != "outbound":
            raise HTTPException(
                status_code=400,
                detail="只有待取件 outbound 狀態可以確認取件",
            )

        next_location = payload.get("current_location") or "已由使用者取回"

        result = db.execute(
            text(
                """
                UPDATE samples
                SET
                    status = 'picked_up',
                    current_location = :next_location,
                    picked_up_at = NOW(),
                    picked_up_by = :operator_name,
                    updated_at = NOW()
                WHERE id = :sample_id
                RETURNING *
                """
            ),
            {
                "sample_id": sample_id,
                "next_location": next_location,
                "operator_name": operator_name,
            },
        )

        update_all_wips_location(
            db=db,
            sample_id=sample_id,
            next_location=next_location,
        )

        db.execute(
            text(
                """
                INSERT INTO sample_histories (
                    sample_id,
                    action,
                    from_status,
                    to_status,
                    description,
                    operator_name
                )
                VALUES (
                    :sample_id,
                    'pickup_confirmed',
                    :from_status,
                    'picked_up',
                    '廠區確認取件，樣品已由使用者取回',
                    :operator_name
                )
                """
            ),
            {
                "sample_id": sample_id,
                "from_status": sample["status"],
                "operator_name": operator_name,
            },
        )

        db.commit()

        return dict(result.fetchone()._mapping)

    if action == "split":
        wips = payload.get("wips")

        if not isinstance(wips, list) or len(wips) == 0:
            raise HTTPException(
                status_code=400,
                detail="wips must be a non-empty list when action is split",
            )

        next_location = normalize_location_for_action(
            payload.get("current_location"),
            current_lab,
            "實驗暫存區",
        )

        created_wips = []

        db.execute(
            text(
                """
                UPDATE samples
                SET
                    status = 'split',
                    current_location = :next_location,
                    updated_at = NOW()
                WHERE id = :sample_id
                """
            ),
            {
                "sample_id": sample_id,
                "next_location": next_location,
            },
        )

        db.execute(
            text(
                """
                INSERT INTO sample_histories (
                    sample_id,
                    action,
                    from_status,
                    to_status,
                    description,
                    operator_name
                )
                VALUES (
                    :sample_id,
                    'split',
                    :from_status,
                    'split',
                    :description,
                    :operator_name
                )
                """
            ),
            {
                "sample_id": sample_id,
                "from_status": sample["status"],
                "description": f"樣品分貨並建立 WIP，樣品位於 {next_location}",
                "operator_name": operator_name,
            },
        )

        for item in wips:
            result = db.execute(
                text(
                    """
                    INSERT INTO wips (
                        wip_no,
                        sample_id,
                        order_no,
                        lab_name,
                        experiment_item,
                        priority,
                        status,
                        progress,
                        current_location,
                        note
                    )
                    VALUES (
                        :wip_no,
                        :sample_id,
                        :order_no,
                        :lab_name,
                        :experiment_item,
                        :priority,
                        'created',
                        0,
                        :current_location,
                        :note
                    )
                    RETURNING *
                    """
                ),
                {
                    "wip_no": item.get("wip_no"),
                    "sample_id": sample_id,
                    "order_no": sample["order_no"],
                    "lab_name": item.get("lab_name"),
                    "experiment_item": item.get("experiment_item"),
                    "priority": item.get("priority", "normal"),
                    "current_location": item.get("current_location") or next_location,
                    "note": item.get("note"),
                },
            )

            created_wip = dict(result.fetchone()._mapping)
            created_wips.append(created_wip)

            db.execute(
                text(
                    """
                    INSERT INTO wip_histories (
                        wip_id,
                        action,
                        from_status,
                        to_status,
                        description,
                        operator_name
                    )
                    VALUES (
                        :wip_id,
                        'created_from_split',
                        NULL,
                        'created',
                        :description,
                        :operator_name
                    )
                    """
                ),
                {
                    "wip_id": created_wip["id"],
                    "description": f"由樣品 {sample['sample_no']} 分貨建立 WIP，位置：{next_location}",
                    "operator_name": operator_name,
                },
            )

        db.commit()

        return {
            "message": "Sample split successfully",
            "sample_id": sample_id,
            "current_location": next_location,
            "created_wips": created_wips,
        }

    raise HTTPException(status_code=400, detail="Unsupported action")

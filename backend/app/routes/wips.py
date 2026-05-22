from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db

router = APIRouter(
    prefix="/api/wips",
    tags=["wips"],
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


@router.get("")
def get_wips(
    request: Request,
    status: str | None = Query(default=None),
    include_all_for_flow: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    current_user = get_active_user(request)
    role = current_user.get("role")

    if include_all_for_flow and role in ("lab_staff", "lab_supervisor", "system_admin"):
        where_clauses = []
        params = {}
    else:
        where_clauses, params = build_wip_visibility_filter(current_user)

    if status:
        where_clauses.append("w.status = :status")
        params["status"] = status

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    result = db.execute(
        text(
            f"""
            SELECT
                w.id,
                w.wip_no,
                w.sample_id,
                w.order_no,
                w.lab_name,
                w.experiment_item,
                w.priority,
                w.status,
                w.progress,
                w.current_location,
                w.scheduled_at,
                w.dispatched_at,
                w.started_at,
                w.completed_at,
                w.terminated_at,
                w.note,
                w.created_at,
                w.updated_at
            FROM wips w
            LEFT JOIN samples s
                ON s.id = w.sample_id
            {where_sql}
            ORDER BY w.created_at DESC
            """
        ),
        params,
    )

    return [dict(row._mapping) for row in result]


@router.get("/{wip_id}")
def get_wip(
    wip_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    current_user = get_active_user(request)
    wip = get_wip_or_404(wip_id, db)
    sample = get_sample_by_id(wip["sample_id"], db)

    if not can_view_wip(current_user, wip, sample):
        raise HTTPException(status_code=403, detail="You do not have permission to view this WIP")

    return wip


@router.get("/{wip_id}/history")
def get_wip_history(
    wip_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    current_user = get_active_user(request)
    wip = get_wip_or_404(wip_id, db)
    sample = get_sample_by_id(wip["sample_id"], db)

    if not can_view_wip(current_user, wip, sample):
        raise HTTPException(status_code=403, detail="You do not have permission to view this WIP")

    result = db.execute(
        text(
            """
            SELECT
                id,
                wip_id,
                action,
                from_status,
                to_status,
                description,
                operator_name,
                created_at
            FROM wip_histories
            WHERE wip_id = :wip_id
            ORDER BY created_at DESC
            """
        ),
        {"wip_id": wip_id},
    )

    return [dict(row._mapping) for row in result]


@router.patch("/{wip_id}")
def update_wip(
    wip_id: str,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
):
    current_user = get_active_user(request)
    wip = get_wip_or_404(wip_id, db)

    if not can_manage_wip(current_user, wip):
        raise HTTPException(status_code=403, detail="You do not have permission to update this WIP")

    result = db.execute(
        text(
            """
            UPDATE wips
            SET
                lab_name = COALESCE(:lab_name, lab_name),
                experiment_item = COALESCE(:experiment_item, experiment_item),
                priority = COALESCE(:priority, priority),
                current_location = COALESCE(:current_location, current_location),
                note = COALESCE(:note, note),
                updated_at = NOW()
            WHERE id = :wip_id
            RETURNING *
            """
        ),
        {
            "wip_id": wip_id,
            "lab_name": payload.get("lab_name"),
            "experiment_item": payload.get("experiment_item"),
            "priority": payload.get("priority"),
            "current_location": payload.get("current_location"),
            "note": payload.get("note"),
        },
    )

    db.commit()

    return dict(result.fetchone()._mapping)


@router.post("/{wip_id}/actions")
def wip_action(
    wip_id: str,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
):
    wip = get_wip_or_404(wip_id, db)
    current_user = get_active_user(request)

    if not can_manage_wip(current_user, wip):
        raise HTTPException(status_code=403, detail="You do not have permission to operate this WIP")

    current_lab = get_user_lab(current_user)

    action = payload.get("action")

    if action not in (
        "send_to_schedule",
        "mark_scheduled",
        "mark_dispatched",
        "start",
        "pause",
        "resume",
        "complete",
        "terminate",
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "action must be one of: send_to_schedule, mark_scheduled, "
                "mark_dispatched, start, pause, resume, complete, terminate"
            ),
        )

    operator_name = payload.get("operator_name") or current_user.get("name")

    if not operator_name:
        raise HTTPException(
            status_code=400,
            detail="operator_name is required",
        )

    status_map = {
        "send_to_schedule": "waiting_schedule",
        "mark_scheduled": "scheduled",
        "mark_dispatched": "dispatched",
        "start": "running",
        "pause": "paused",
        "resume": "running",
        "complete": "completed",
        "terminate": "terminated",
    }

    description_map = {
        "send_to_schedule": "WIP 送入待排程",
        "mark_scheduled": "WIP 標記為已排程",
        "mark_dispatched": "WIP 標記為已派工",
        "start": "WIP 開始執行，樣品移至機台區",
        "pause": "WIP 暫停",
        "resume": "WIP 恢復執行",
        "complete": "WIP 完成，樣品回到實驗暫存區",
        "terminate": "WIP 終止",
    }

    new_status = status_map[action]
    description = payload.get("description") or description_map[action]

    extra_sql = ""
    extra_params = {}

    if action == "mark_scheduled":
        extra_sql += ", scheduled_at = NOW()"

    if action == "mark_dispatched":
        extra_sql += ", dispatched_at = NOW()"

    if action == "start":
        next_location = payload.get("current_location") or machine_location(current_lab)
        extra_sql += ", started_at = NOW(), current_location = :next_location"
        extra_params["next_location"] = next_location

    if action == "resume":
        next_location = payload.get("current_location") or machine_location(current_lab)
        extra_sql += ", current_location = :next_location"
        extra_params["next_location"] = next_location

    if action == "complete":
        next_location = payload.get("current_location") or experiment_temp_location(current_lab)
        extra_sql += ", completed_at = NOW(), progress = 100, current_location = :next_location"
        extra_params["next_location"] = next_location

    if action == "terminate":
        extra_sql += ", terminated_at = NOW()"

    sql = f"""
        UPDATE wips
        SET
            status = :new_status,
            updated_at = NOW()
            {extra_sql}
        WHERE id = :wip_id
        RETURNING *
    """

    params = {
        "wip_id": wip_id,
        "new_status": new_status,
    }
    params.update(extra_params)

    result = db.execute(text(sql), params)
    updated_wip = dict(result.fetchone()._mapping)

    if action in ("start", "resume", "complete"):
        next_location = extra_params.get("next_location")

        if next_location:
            db.execute(
                text(
                    """
                    UPDATE samples
                    SET
                        current_location = :next_location,
                        updated_at = NOW()
                    WHERE id = :sample_id
                    """
                ),
                {
                    "sample_id": wip["sample_id"],
                    "next_location": next_location,
                },
            )

            db.execute(
                text(
                    """
                    UPDATE wips
                    SET
                        current_location = :next_location,
                        updated_at = NOW()
                    WHERE sample_id = :sample_id
                      AND status <> 'completed'
                """
                ),
                {
                    "sample_id": wip["sample_id"],
                    "next_location": next_location,
                },
            )

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
                :action,
                :from_status,
                :to_status,
                :description,
                :operator_name
            )
            """
        ),
        {
            "wip_id": wip_id,
            "action": action,
            "from_status": wip["status"],
            "to_status": new_status,
            "description": description,
            "operator_name": operator_name,
        },
    )

    db.commit()

    return updated_wip
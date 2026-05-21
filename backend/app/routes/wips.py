from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db

router = APIRouter(
    prefix="/api/wips",
    tags=["wips"],
)


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


@router.get("")
def get_wips(db: Session = Depends(get_db)):
    result = db.execute(
        text(
            """
            SELECT
                id,
                wip_no,
                sample_id,
                order_no,
                lab_name,
                experiment_item,
                priority,
                status,
                progress,
                current_location,
                scheduled_at,
                dispatched_at,
                started_at,
                completed_at,
                terminated_at,
                note,
                created_at,
                updated_at
            FROM wips
            ORDER BY created_at DESC
            """
        )
    )

    return [dict(row._mapping) for row in result]


@router.get("/{wip_id}")
def get_wip(wip_id: str, db: Session = Depends(get_db)):
    return get_wip_or_404(wip_id, db)


@router.get("/{wip_id}/history")
def get_wip_history(wip_id: str, db: Session = Depends(get_db)):
    get_wip_or_404(wip_id, db)

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
    db: Session = Depends(get_db),
):
    get_wip_or_404(wip_id, db)

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
    db: Session = Depends(get_db),
):
    wip = get_wip_or_404(wip_id, db)
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

    # TODO(auth):
    # operator_name 目前先由 request body 傳入文字，格式建議為「實驗室／姓名」。
    # 等 /api/me 完成後，改由登入者資訊自動帶入：
    # operator_user_id = current_user.id
    # operator_name = current_user.name
    # operator_lab = current_user.lab_name
    operator_name = payload.get("operator_name")

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
        "start": "WIP 開始執行",
        "pause": "WIP 暫停",
        "resume": "WIP 恢復執行",
        "complete": "WIP 完成",
        "terminate": "WIP 終止",
    }

    new_status = status_map[action]
    description = payload.get("description") or description_map[action]

    extra_sql = ""

    if action == "mark_scheduled":
        extra_sql = ", scheduled_at = NOW()"

    if action == "mark_dispatched":
        extra_sql = ", dispatched_at = NOW()"

    if action == "start":
        extra_sql = ", started_at = NOW()"

    if action == "complete":
        extra_sql = ", completed_at = NOW(), progress = 100"

    if action == "terminate":
        extra_sql = ", terminated_at = NOW()"

    sql = f"""
        UPDATE wips
        SET
            status = :new_status,
            updated_at = NOW()
            {extra_sql}
        WHERE id = :wip_id
        RETURNING *
    """

    result = db.execute(
        text(sql),
        {
            "wip_id": wip_id,
            "new_status": new_status,
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

    return dict(result.fetchone()._mapping)
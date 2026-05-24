from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

router = APIRouter(
    prefix="/api/wips",
    tags=["wips"],
)

from app.services.wip_service import *  # noqa: F403


def build_wip_flow_visibility_filter(current_user: dict):
    """給 transfer flow 使用的 WIP 查詢範圍。

    一般 WIP 管理頁只看自己 Lab 的 WIP。
    但 transfer flow 需要判斷同一個 sample 底下所有 Lab 的 WIP 是否完成，
    否則 LabB 會看不到 LabA 已完成的 WIP，誤判 LabA 還沒完成，導致又送回 LabA。
    """

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

        where_clauses.append(
            """
            (
                s.current_location LIKE :current_lab_prefix
                OR EXISTS (
                    SELECT 1
                    FROM wips related_wips
                    WHERE related_wips.sample_id = w.sample_id
                      AND related_wips.lab_name = :current_lab
                )
                OR EXISTS (
                    SELECT 1
                    FROM transfers sample_transfers
                    WHERE sample_transfers.target_type = 'sample'
                      AND sample_transfers.target_id = s.id
                      AND (
                          sample_transfers.from_lab = :current_lab
                          OR sample_transfers.to_lab = :current_lab
                      )
                )
                OR EXISTS (
                    SELECT 1
                    FROM transfers wip_transfers
                    WHERE wip_transfers.target_type = 'wip'
                      AND wip_transfers.target_id = w.id
                      AND (
                          wip_transfers.from_lab = :current_lab
                          OR wip_transfers.to_lab = :current_lab
                      )
                )
            )
            """
        )

        return where_clauses, params

    where_clauses.append("1 = 0")
    return where_clauses, params


@router.get("")
async def get_wips(
    request: Request,
    status: str | None = Query(default=None),
    include_all_for_flow: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
):
    current_user = get_active_user(request)

    if include_all_for_flow:
        where_clauses, params = build_wip_flow_visibility_filter(current_user)
    else:
        where_clauses, params = build_wip_visibility_filter(current_user)

    if status:
        where_clauses.append("w.status = :status")
        params["status"] = status

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    result = await db.execute(
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
async def get_wip(
    wip_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    current_user = get_active_user(request)
    wip = await get_wip_or_404(wip_id, db)
    sample = await get_sample_by_id(wip["sample_id"], db)

    if not await can_view_wip(current_user, wip, sample, db):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view this WIP",
        )

    return wip


@router.get("/{wip_id}/history")
async def get_wip_history(
    wip_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    current_user = get_active_user(request)
    wip = await get_wip_or_404(wip_id, db)
    sample = await get_sample_by_id(wip["sample_id"], db)

    if not await can_view_wip(current_user, wip, sample):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view this WIP",
        )

    result = await db.execute(
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
async def update_wip(
    wip_id: str,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    current_user = get_active_user(request)
    wip = await get_wip_or_404(wip_id, db)

    if not can_manage_wip(current_user, wip):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to update this WIP",
        )

    result = await db.execute(
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

    updated_wip = dict(result.fetchone()._mapping)
    await db.commit()

    return updated_wip


@router.post("/{wip_id}/actions")
async def wip_action(
    wip_id: str,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    wip = await get_wip_or_404(wip_id, db)
    current_user = get_active_user(request)

    if not can_manage_wip(current_user, wip):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to operate this WIP",
        )

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

    result = await db.execute(text(sql), params)
    updated_wip = dict(result.fetchone()._mapping)

    if action in ("start", "resume", "complete"):
        next_location = extra_params.get("next_location")

        if next_location:
            await db.execute(
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
                    "sample_id": wip["sample_id"],
                    "current_lab": current_lab,
                    "next_location": next_location,
                },
            )

    await db.execute(
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

    await db.commit()

    return updated_wip

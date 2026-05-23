import psycopg
from fastapi import APIRouter, Header, HTTPException

from database import get_connection
from dependencies import (
    ensure_same_lab,
    get_user,
    lab_filter_sql,
    require_lab_scope,
    require_role,
)
from schemas import AssignRequest, DispatchCreate, ReplanRequest, SuggestRequest
from serializers import dispatch_from_row, list_response, response
from services.scheduling import REPLAN_STRATEGIES, apply_schedule_suggestion


router = APIRouter()


@router.get("/api/dispatches")
def get_dispatches(x_user_id: str | None = Header(default=None)) -> dict[str, object]:
    with get_connection() as conn:
        user = get_user(conn, x_user_id)
        filter_sql, params = lab_filter_sql(user)
        rows = conn.execute(
            f"""
            SELECT *
            FROM dispatches
            {filter_sql}
            ORDER BY
                CASE WHEN scheduled_start IS NULL THEN 1 ELSE 0 END,
                scheduled_start ASC,
                dispatch_id ASC
            """,
            params,
        ).fetchall()
    return list_response([dispatch_from_row(row) for row in rows])


@router.post("/api/dispatches")
def create_dispatch(
    payload: DispatchCreate, x_user_id: str | None = Header(default=None)
) -> dict[str, object]:
    with get_connection() as conn:
        user = get_user(conn, x_user_id)
        require_role(user, {"實驗室人員", "實驗室小主管"})
        lab = payload.lab or require_lab_scope(user)
        ensure_same_lab(user, lab)
        try:
            row = conn.execute(
                """
                INSERT INTO dispatches (
                    dispatch_id, wip_id, order_id, experiment_item,
                    priority, lab, due_at, status, created_by
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, '待派工', %s)
                RETURNING *
                """,
                (
                    payload.dispatchId,
                    payload.wipId,
                    payload.orderId,
                    payload.experimentItem,
                    payload.priority,
                    lab,
                    payload.dueAt,
                    user.name,
                ),
            ).fetchone()
        except psycopg.errors.UniqueViolation as exc:
            raise HTTPException(
                status_code=409, detail="Dispatch already exists"
            ) from exc
    return response(dispatch_from_row(row), "dispatch created")


@router.post("/api/dispatches/suggest")
def suggest_dispatches(
    payload: SuggestRequest, x_user_id: str | None = Header(default=None)
) -> dict[str, object]:
    with get_connection() as conn:
        user = get_user(conn, x_user_id)
        require_role(user, {"實驗室人員", "實驗室小主管", "系統管理者"})
        rows = apply_schedule_suggestion(conn, payload.strategy, user)

    return response(
        {
            "strategy": payload.strategy,
            "dispatches": [dispatch_from_row(row) for row in rows],
        },
        "schedule suggestion generated",
    )


@router.post("/api/dispatches/replan")
def replan_dispatches(
    payload: ReplanRequest, x_user_id: str | None = Header(default=None)
) -> dict[str, object]:
    with get_connection() as conn:
        user = get_user(conn, x_user_id)
        require_role(user, {"實驗室人員", "實驗室小主管", "系統管理者"})
        strategy = REPLAN_STRATEGIES.get(payload.reason, payload.strategy)
        filter_sql, params = lab_filter_sql(user)
        conn.execute(
            f"""
            UPDATE dispatches
            SET status = '待派工',
                suggested_machine_id = NULL,
                scheduled_start = NULL,
                scheduled_end = NULL,
                strategy = NULL,
                replan_reason = %s
            WHERE status = '排程中'
            {"AND lab = %s" if filter_sql else ""}
            """,
            (payload.reason, *params),
        )
        rows = apply_schedule_suggestion(conn, strategy, user, payload.reason)
    return response(
        {
            "reason": payload.reason,
            "strategy": strategy,
            "dispatches": [dispatch_from_row(row) for row in rows],
        },
        "dispatches replanned",
    )


@router.post("/api/dispatches/{dispatch_id}/assign")
def assign_dispatch(
    dispatch_id: str,
    payload: AssignRequest,
    x_user_id: str | None = Header(default=None),
) -> dict[str, object]:
    with get_connection() as conn:
        user = get_user(conn, x_user_id)
        require_role(user, {"實驗室人員", "實驗室小主管"})
        dispatch = conn.execute(
            "SELECT * FROM dispatches WHERE dispatch_id = %s", (dispatch_id,)
        ).fetchone()
        machine = conn.execute(
            "SELECT * FROM machines WHERE machine_id = %s", (payload.machineId,)
        ).fetchone()
        recipe = conn.execute(
            "SELECT * FROM recipes WHERE recipe_id = %s", (payload.recipeId,)
        ).fetchone()

        if dispatch is None:
            raise HTTPException(status_code=404, detail="Dispatch not found")
        if machine is None:
            raise HTTPException(status_code=404, detail="Machine not found")
        if recipe is None:
            raise HTTPException(status_code=404, detail="Recipe not found")
        ensure_same_lab(user, str(dispatch["lab"]))
        ensure_same_lab(user, str(machine["lab"]))
        if dispatch["lab"] != machine["lab"]:
            raise HTTPException(
                status_code=400, detail="Dispatch and machine are in different labs"
            )
        if machine["status"] in ["故障中", "保養中", "停用"]:
            raise HTTPException(status_code=400, detail="Machine is not assignable")
        if dispatch["experiment_item"] not in machine["supported_items"]:
            raise HTTPException(
                status_code=400, detail="Machine does not support this item"
            )
        if payload.machineId not in recipe["machine_ids"]:
            raise HTTPException(
                status_code=400, detail="Recipe is not available for machine"
            )
        if recipe["experiment_item"] != dispatch["experiment_item"]:
            raise HTTPException(
                status_code=400, detail="Recipe does not match WIP item"
            )

        row = conn.execute(
            """
            UPDATE dispatches
            SET status = '待上機',
                assigned_machine_id = %s,
                assigned_recipe_id = %s,
                scheduled_start = %s,
                scheduled_end = %s,
                assigned_by = %s
            WHERE dispatch_id = %s
            RETURNING *
            """,
            (
                payload.machineId,
                payload.recipeId,
                payload.scheduledStart,
                payload.scheduledEnd,
                user.name,
                dispatch_id,
            ),
        ).fetchone()

    return response(dispatch_from_row(row), "dispatch assigned")

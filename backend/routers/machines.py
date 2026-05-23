import psycopg
from fastapi import APIRouter, Header, HTTPException

from database import get_connection
from dependencies import ensure_same_lab, get_user, lab_filter_sql, require_role
from schemas import MachineCreate, MachineStatusUpdate, MachineUpdate
from serializers import list_response, machine_from_row, response


router = APIRouter()


@router.get("/api/machines")
def get_machines(x_user_id: str | None = Header(default=None)) -> dict[str, object]:
    with get_connection() as conn:
        user = get_user(conn, x_user_id)
        filter_sql, params = lab_filter_sql(user)
        rows = conn.execute(
            f"SELECT * FROM machines{filter_sql} ORDER BY machine_id",
            params,
        ).fetchall()
    return list_response([machine_from_row(row) for row in rows])


@router.post("/api/machines")
def create_machine(
    payload: MachineCreate, x_user_id: str | None = Header(default=None)
) -> dict[str, object]:
    with get_connection() as conn:
        user = get_user(conn, x_user_id)
        require_role(user, {"實驗室人員", "實驗室小主管", "系統管理者"})
        ensure_same_lab(user, payload.lab)
        try:
            row = conn.execute(
                """
                INSERT INTO machines (
                    machine_id, name, lab, status, supported_items,
                    utilization, owner, last_maintenance
                )
                VALUES (%s, %s, %s, '閒置', %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    payload.machineId,
                    payload.name,
                    payload.lab,
                    payload.supportedItems,
                    payload.utilization,
                    payload.owner,
                    payload.lastMaintenance,
                ),
            ).fetchone()
        except psycopg.errors.UniqueViolation as exc:
            raise HTTPException(
                status_code=409, detail="Machine already exists"
            ) from exc
    return response(machine_from_row(row), "machine created")


@router.patch("/api/machines/{machine_id}/status")
def update_machine_status(
    machine_id: str,
    payload: MachineStatusUpdate,
    x_user_id: str | None = Header(default=None),
) -> dict[str, object]:
    with get_connection() as conn:
        user = get_user(conn, x_user_id)
        require_role(user, {"實驗室人員", "實驗室小主管", "系統管理者"})
        machine = conn.execute(
            "SELECT * FROM machines WHERE machine_id = %s", (machine_id,)
        ).fetchone()
        if machine is None:
            raise HTTPException(status_code=404, detail="Machine not found")
        ensure_same_lab(user, str(machine["lab"]))
        row = conn.execute(
            """
            UPDATE machines
            SET status = %s
            WHERE machine_id = %s
            RETURNING *
            """,
            (payload.status, machine_id),
        ).fetchone()
    return response(machine_from_row(row), "machine status updated")


@router.patch("/api/machines/{machine_id}")
def update_machine(
    machine_id: str,
    payload: MachineUpdate,
    x_user_id: str | None = Header(default=None),
) -> dict[str, object]:
    with get_connection() as conn:
        user = get_user(conn, x_user_id)
        require_role(user, {"實驗室人員", "實驗室小主管", "系統管理者"})
        machine = conn.execute(
            "SELECT * FROM machines WHERE machine_id = %s", (machine_id,)
        ).fetchone()
        if machine is None:
            raise HTTPException(status_code=404, detail="Machine not found")
        ensure_same_lab(user, str(machine["lab"]))
        ensure_same_lab(user, payload.lab)
        row = conn.execute(
            """
            UPDATE machines
            SET name = %s,
                lab = %s,
                supported_items = %s,
                utilization = %s,
                owner = %s,
                last_maintenance = %s
            WHERE machine_id = %s
            RETURNING *
            """,
            (
                payload.name,
                payload.lab,
                payload.supportedItems,
                payload.utilization,
                payload.owner,
                payload.lastMaintenance,
                machine_id,
            ),
        ).fetchone()
    return response(machine_from_row(row), "machine updated")

from fastapi import APIRouter, Header

from database import get_connection
from dependencies import can_view_all_labs, get_user, lab_filter_sql
from serializers import dispatch_from_row, machine_from_row, response


router = APIRouter()


@router.get("/api/dashboard")
def get_dashboard(x_user_id: str | None = Header(default=None)) -> dict[str, object]:
    with get_connection() as conn:
        user = get_user(conn, x_user_id)
        filter_sql, params = lab_filter_sql(user)
        machines = conn.execute(
            f"SELECT * FROM machines{filter_sql} ORDER BY lab, machine_id",
            params,
        ).fetchall()
        dispatches = conn.execute(
            f"SELECT * FROM dispatches{filter_sql} ORDER BY lab, due_at, dispatch_id",
            params,
        ).fetchall()
        lab_rows = conn.execute(
            f"""
            SELECT
                labs.lab,
                COUNT(DISTINCT machines.machine_id) AS machine_count,
                COUNT(DISTINCT dispatches.dispatch_id) AS dispatch_count,
                COUNT(DISTINCT dispatches.dispatch_id)
                    FILTER (WHERE dispatches.status = '待派工') AS pending_count,
                COUNT(DISTINCT dispatches.dispatch_id)
                    FILTER (WHERE dispatches.status = '排程中') AS scheduling_count,
                COUNT(DISTINCT dispatches.dispatch_id)
                    FILTER (WHERE dispatches.status = '待上機') AS ready_count,
                COUNT(DISTINCT machines.machine_id)
                    FILTER (WHERE machines.status IN ('故障中', '保養中', '停用')) AS blocked_machine_count,
                COALESCE(ROUND(AVG(machines.utilization)), 0) AS avg_utilization
            FROM (
                SELECT lab FROM machines
                UNION
                SELECT lab FROM dispatches
            ) labs
            LEFT JOIN machines ON machines.lab = labs.lab
            LEFT JOIN dispatches ON dispatches.lab = labs.lab
            {filter_sql.replace("lab", "labs.lab") if filter_sql else ""}
            GROUP BY labs.lab
            ORDER BY labs.lab
            """,
            params,
        ).fetchall()

    pending = sum(1 for row in dispatches if row["status"] == "待派工")
    scheduling = sum(1 for row in dispatches if row["status"] == "排程中")
    ready = sum(1 for row in dispatches if row["status"] == "待上機")
    blocked = sum(
        1 for row in machines if row["status"] in ["故障中", "保養中", "停用"]
    )
    avg_utilization = (
        round(sum(int(row["utilization"]) for row in machines) / len(machines))
        if machines
        else 0
    )

    return response(
        {
            "scope": "all" if can_view_all_labs(user) else user.lab,
            "user": user,
            "kpis": {
                "pendingDispatches": pending,
                "schedulingDispatches": scheduling,
                "readyDispatches": ready,
                "blockedMachines": blocked,
                "machineCount": len(machines),
                "avgUtilization": avg_utilization,
            },
            "labs": [
                {
                    "lab": row["lab"],
                    "machineCount": int(row["machine_count"]),
                    "dispatchCount": int(row["dispatch_count"]),
                    "pendingCount": int(row["pending_count"]),
                    "schedulingCount": int(row["scheduling_count"]),
                    "readyCount": int(row["ready_count"]),
                    "blockedMachineCount": int(row["blocked_machine_count"]),
                    "avgUtilization": int(row["avg_utilization"]),
                }
                for row in lab_rows
            ],
            "machines": [machine_from_row(row) for row in machines],
            "dispatches": [dispatch_from_row(row) for row in dispatches],
        },
        "dashboard loaded",
    )

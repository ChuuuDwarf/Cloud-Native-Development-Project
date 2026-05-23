import os
import time
from datetime import datetime, timedelta
from typing import Literal

import psycopg
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field


MachineStatus = Literal["閒置", "使用中", "保養中", "故障中", "停用"]
WipStatus = Literal["待派工", "排程中", "待上機"]
ScheduleStrategy = Literal[
    "FIFO", "Priority First", "Earliest Due Date", "Least Setup Change", "Hybrid"
]
UserRole = Literal[
    "廠區使用者",
    "實驗室人員",
    "實驗室小主管",
    "實驗室大主管",
    "系統管理者",
]

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://lims:lims@127.0.0.1:5432/lims"
)


class Machine(BaseModel):
    machineId: str
    name: str
    lab: str
    status: MachineStatus
    supportedItems: list[str]
    utilization: int = Field(ge=0, le=100)
    owner: str
    lastMaintenance: str


class User(BaseModel):
    userId: str
    name: str
    role: UserRole
    department: str
    lab: str | None = None


class MachineCreate(BaseModel):
    machineId: str
    name: str
    lab: str
    supportedItems: list[str]
    owner: str
    utilization: int = Field(default=0, ge=0, le=100)
    lastMaintenance: str = "尚未保養"


class MachineStatusUpdate(BaseModel):
    status: MachineStatus


class MachineUpdate(BaseModel):
    name: str
    lab: str
    supportedItems: list[str]
    owner: str
    utilization: int = Field(ge=0, le=100)
    lastMaintenance: str


class Recipe(BaseModel):
    recipeId: str
    name: str
    version: str
    experimentItem: str
    machineIds: list[str]
    method: str
    parameters: dict[str, str]
    updatedBy: str
    updatedAt: str


class RecipeCreate(BaseModel):
    recipeId: str
    name: str
    version: str
    experimentItem: str
    machineIds: list[str]
    method: str
    parameters: dict[str, str] = Field(default_factory=dict)
    updatedBy: str


class Dispatch(BaseModel):
    dispatchId: str
    wipId: str
    orderId: str
    experimentItem: str
    priority: str
    lab: str
    dueAt: str
    status: WipStatus
    suggestedMachineId: str | None = None
    assignedMachineId: str | None = None
    assignedRecipeId: str | None = None
    scheduledStart: str | None = None
    scheduledEnd: str | None = None
    createdBy: str | None = None
    assignedBy: str | None = None
    strategy: str | None = None
    replanReason: str | None = None


class DispatchCreate(BaseModel):
    dispatchId: str
    wipId: str
    orderId: str
    experimentItem: str
    priority: str
    lab: str | None = None
    dueAt: str


class SuggestRequest(BaseModel):
    strategy: ScheduleStrategy = "FIFO"


class AssignRequest(BaseModel):
    machineId: str
    recipeId: str
    scheduledStart: str
    scheduledEnd: str


class ReplanRequest(BaseModel):
    reason: str
    strategy: ScheduleStrategy = "Hybrid"


app = FastAPI(title="LIMS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


REPLAN_STRATEGIES: dict[str, ScheduleStrategy] = {
    "機台故障重排": "Least Setup Change",
    "特急單插單重排": "Priority First",
    "前站延誤重排": "Earliest Due Date",
    "人員不足重排": "Hybrid",
}


def get_connection() -> psycopg.Connection:
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def response(data: object, message: str = "success") -> dict[str, object]:
    return {"data": data, "message": message}


def list_response(data: list[object], message: str = "success") -> dict[str, object]:
    return {"data": data, "total": len(data), "message": message}


def machine_from_row(row: dict[str, object]) -> Machine:
    return Machine(
        machineId=str(row["machine_id"]),
        name=str(row["name"]),
        lab=str(row["lab"]),
        status=row["status"],
        supportedItems=list(row["supported_items"]),
        utilization=int(row["utilization"]),
        owner=str(row["owner"]),
        lastMaintenance=str(row["last_maintenance"]),
    )


def user_from_row(row: dict[str, object]) -> User:
    return User(
        userId=str(row["user_id"]),
        name=str(row["name"]),
        role=row["role"],
        department=str(row["department"]),
        lab=row["lab"],
    )


def recipe_from_row(row: dict[str, object]) -> Recipe:
    return Recipe(
        recipeId=str(row["recipe_id"]),
        name=str(row["name"]),
        version=str(row["version"]),
        experimentItem=str(row["experiment_item"]),
        machineIds=list(row["machine_ids"]),
        method=str(row["method"]),
        parameters=dict(row["parameters"]),
        updatedBy=str(row["updated_by"]),
        updatedAt=row["updated_at"].strftime("%Y-%m-%d %H:%M"),
    )


def dispatch_from_row(row: dict[str, object]) -> Dispatch:
    return Dispatch(
        dispatchId=str(row["dispatch_id"]),
        wipId=str(row["wip_id"]),
        orderId=str(row["order_id"]),
        experimentItem=str(row["experiment_item"]),
        priority=str(row["priority"]),
        lab=str(row["lab"]),
        dueAt=str(row["due_at"]),
        status=row["status"],
        suggestedMachineId=row["suggested_machine_id"],
        assignedMachineId=row["assigned_machine_id"],
        assignedRecipeId=row["assigned_recipe_id"],
        scheduledStart=row["scheduled_start"],
        scheduledEnd=row["scheduled_end"],
        createdBy=row["created_by"],
        assignedBy=row["assigned_by"],
        strategy=row["strategy"],
        replanReason=row["replan_reason"],
    )


def get_user(conn: psycopg.Connection, user_id: str | None) -> User:
    if not user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header is required")
    row = conn.execute("SELECT * FROM users WHERE user_id = %s", (user_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="Unknown user")
    return user_from_row(row)


def require_role(user: User, allowed_roles: set[UserRole]) -> None:
    if user.role not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail=f"{user.role} cannot perform this role C operation",
        )


def can_view_all_labs(user: User) -> bool:
    return user.role in {"實驗室大主管", "系統管理者"}


def require_lab_scope(user: User) -> str:
    if not user.lab:
        raise HTTPException(status_code=403, detail="This operation requires a lab-scoped user")
    return user.lab


def lab_filter_sql(user: User, column: str = "lab") -> tuple[str, tuple[object, ...]]:
    if can_view_all_labs(user):
        return "", ()
    return f" WHERE {column} = %s", (require_lab_scope(user),)


def ensure_same_lab(user: User, lab: str) -> None:
    if can_view_all_labs(user):
        return
    if lab != require_lab_scope(user):
        raise HTTPException(status_code=403, detail="Cannot access another lab")


def priority_rank(priority: str) -> int:
    return {"特急": 0, "高": 1, "一般": 2}.get(priority, 3)


def sorted_dispatches(
    dispatch_rows: list[dict[str, object]], strategy: ScheduleStrategy
) -> list[dict[str, object]]:
    if strategy == "Priority First":
        return sorted(dispatch_rows, key=lambda row: (priority_rank(str(row["priority"])), row["due_at"]))
    if strategy == "Earliest Due Date":
        return sorted(dispatch_rows, key=lambda row: (row["due_at"], priority_rank(str(row["priority"]))))
    if strategy == "Least Setup Change":
        return sorted(dispatch_rows, key=lambda row: (row["experiment_item"], row["dispatch_id"]))
    if strategy == "Hybrid":
        return sorted(
            dispatch_rows,
            key=lambda row: (
                priority_rank(str(row["priority"])),
                row["due_at"],
                row["experiment_item"],
            ),
        )
    return sorted(dispatch_rows, key=lambda row: row["dispatch_id"])


def apply_schedule_suggestion(
    conn: psycopg.Connection,
    strategy: ScheduleStrategy,
    user: User,
    replan_reason: str | None = None,
) -> list[dict[str, object]]:
    dispatch_filter, dispatch_params = lab_filter_sql(user)
    dispatch_rows = conn.execute(
        f"""
        SELECT *
        FROM dispatches
        {dispatch_filter if dispatch_filter else "WHERE TRUE"}
          AND status IN ('待派工', '排程中')
        ORDER BY dispatch_id
        """,
        dispatch_params,
    ).fetchall()
    dispatch_rows = sorted_dispatches(dispatch_rows, strategy)
    machine_filter, machine_params = lab_filter_sql(user)
    machine_rows = conn.execute(
        f"""
        SELECT *
        FROM machines
        {machine_filter if machine_filter else "WHERE TRUE"}
          AND status NOT IN ('故障中', '保養中', '停用')
        ORDER BY utilization ASC, machine_id ASC
        """,
        machine_params,
    ).fetchall()

    shift_start = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    for index, dispatch in enumerate(dispatch_rows):
        matched_machine = next(
            (
                machine
                for machine in machine_rows
                if dispatch["experiment_item"] in machine["supported_items"]
                and dispatch["lab"] == machine["lab"]
            ),
            None,
        )
        if matched_machine is not None:
            scheduled_start = shift_start + timedelta(hours=index * 2)
            scheduled_end = scheduled_start + timedelta(hours=2)
            conn.execute(
                """
                UPDATE dispatches
                SET status = '排程中',
                    suggested_machine_id = %s,
                    scheduled_start = %s,
                    scheduled_end = %s,
                    strategy = %s,
                    replan_reason = %s
                WHERE dispatch_id = %s
                """,
                (
                    matched_machine["machine_id"],
                    scheduled_start.strftime("%Y-%m-%d %H:%M"),
                    scheduled_end.strftime("%Y-%m-%d %H:%M"),
                    strategy,
                    replan_reason,
                    dispatch["dispatch_id"],
                ),
            )

    return conn.execute(
        f"""
        SELECT *
        FROM dispatches
        {dispatch_filter}
        ORDER BY
            CASE WHEN scheduled_start IS NULL THEN 1 ELSE 0 END,
            scheduled_start ASC,
            dispatch_id ASC
        """,
        dispatch_params,
    ).fetchall()


def execute_many(
    conn: psycopg.Connection, query: str, values: list[tuple[object, ...]]
) -> None:
    with conn.cursor() as cursor:
        cursor.executemany(query, values)


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                department TEXT NOT NULL,
                lab TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS machines (
                machine_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                lab TEXT NOT NULL,
                status TEXT NOT NULL,
                supported_items TEXT[] NOT NULL,
                utilization INTEGER NOT NULL DEFAULT 0,
                owner TEXT NOT NULL,
                last_maintenance TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS recipes (
                recipe_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                version TEXT NOT NULL,
                experiment_item TEXT NOT NULL,
                machine_ids TEXT[] NOT NULL,
                method TEXT NOT NULL,
                parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
                updated_by TEXT NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS dispatches (
                dispatch_id TEXT PRIMARY KEY,
                wip_id TEXT NOT NULL,
                order_id TEXT NOT NULL,
                experiment_item TEXT NOT NULL,
                priority TEXT NOT NULL,
                lab TEXT NOT NULL DEFAULT 'LAB A',
                due_at TEXT NOT NULL,
                status TEXT NOT NULL,
                suggested_machine_id TEXT,
                assigned_machine_id TEXT,
                assigned_recipe_id TEXT,
                scheduled_start TEXT,
                scheduled_end TEXT,
                created_by TEXT,
                assigned_by TEXT,
                strategy TEXT,
                replan_reason TEXT
            )
            """
        )
        conn.execute("ALTER TABLE dispatches ADD COLUMN IF NOT EXISTS created_by TEXT")
        conn.execute("ALTER TABLE dispatches ADD COLUMN IF NOT EXISTS assigned_by TEXT")
        conn.execute("ALTER TABLE dispatches ADD COLUMN IF NOT EXISTS strategy TEXT")
        conn.execute("ALTER TABLE dispatches ADD COLUMN IF NOT EXISTS replan_reason TEXT")
        conn.execute("ALTER TABLE dispatches ADD COLUMN IF NOT EXISTS lab TEXT DEFAULT 'LAB A'")
        conn.execute("UPDATE dispatches SET lab = 'LAB A' WHERE lab IS NULL")
        conn.execute("ALTER TABLE dispatches ALTER COLUMN lab SET NOT NULL")
        seed_db(conn)


def seed_db(conn: psycopg.Connection) -> None:
    lab_users = [
        ("u-lab", "林育誠", "實驗室人員", "實驗室", "LAB A"),
        ("u-supervisor", "陳雅婷", "實驗室小主管", "實驗室", "LAB A"),
        ("u-lab-a", "林育誠", "實驗室人員", "實驗室", "LAB A"),
        ("u-supervisor-a", "陳雅婷", "實驗室小主管", "實驗室", "LAB A"),
        ("u-lab-b", "吳佳穎", "實驗室人員", "實驗室", "LAB B"),
        ("u-supervisor-b", "黃柏翰", "實驗室小主管", "實驗室", "LAB B"),
        ("u-lab-c", "周品妤", "實驗室人員", "實驗室", "LAB C"),
        ("u-supervisor-c", "許冠廷", "實驗室小主管", "實驗室", "LAB C"),
        ("u-chief", "謝雅雯", "實驗室大主管", "實驗室", None),
        ("u-admin", "張志明", "系統管理者", "資訊部", None),
    ]
    user_count = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"]
    if user_count == 0:
        execute_many(
            conn,
            """
            INSERT INTO users (user_id, name, role, department, lab)
            VALUES (%s, %s, %s, %s, %s)
            """,
            [
                ("u-factory", "王建國", "廠區使用者", "F12 廠", None),
                ("u-lab-a", "林育誠", "實驗室人員", "實驗室", "LAB A"),
                ("u-supervisor-a", "陳雅婷", "實驗室小主管", "實驗室", "LAB A"),
                ("u-lab-b", "吳佳穎", "實驗室人員", "實驗室", "LAB B"),
                ("u-supervisor-b", "黃柏翰", "實驗室小主管", "實驗室", "LAB B"),
                ("u-lab-c", "周品妤", "實驗室人員", "實驗室", "LAB C"),
                ("u-supervisor-c", "許冠廷", "實驗室小主管", "實驗室", "LAB C"),
                ("u-chief", "謝雅雯", "實驗室大主管", "實驗室", None),
                ("u-admin", "張志明", "系統管理者", "資訊部", None),
            ],
        )
    execute_many(
        conn,
        """
        INSERT INTO users (user_id, name, role, department, lab)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (user_id)
        DO UPDATE SET name = EXCLUDED.name,
                      role = EXCLUDED.role,
                      department = EXCLUDED.department,
                      lab = EXCLUDED.lab
        """,
        lab_users,
    )
    conn.execute("UPDATE machines SET lab = 'LAB A' WHERE lab = '材料分析實驗室'")
    conn.execute("UPDATE machines SET lab = 'LAB B' WHERE lab = '結構分析實驗室'")
    conn.execute("UPDATE machines SET lab = 'LAB C' WHERE lab = '光學實驗室'")
    conn.execute(
        """
        UPDATE dispatches
        SET lab = CASE
            WHEN experiment_item IN ('材料成份分析', '晶格缺陷觀察', '表面形貌分析') THEN 'LAB A'
            WHEN experiment_item IN ('晶體結構分析', '薄膜應力分析') THEN 'LAB B'
            WHEN experiment_item IN ('光學量測', '膜厚量測') THEN 'LAB C'
            ELSE lab
        END
        """
    )

    machine_count = conn.execute("SELECT COUNT(*) AS count FROM machines").fetchone()["count"]
    if machine_count == 0:
        execute_many(
            conn,
            """
            INSERT INTO machines (
                machine_id, name, lab, status, supported_items,
                utilization, owner, last_maintenance
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [
                (
                    "TEM-001",
                    "穿透式電子顯微鏡",
                    "LAB A",
                    "閒置",
                    ["材料成份分析", "晶格缺陷觀察"],
                    48,
                    "林育誠",
                    "2026-05-10",
                ),
                (
                    "XRD-002",
                    "X 光繞射儀",
                    "LAB B",
                    "閒置",
                    ["晶體結構分析", "薄膜應力分析"],
                    35,
                    "陳雅婷",
                    "2026-05-14",
                ),
                (
                    "SEM-001",
                    "掃描式電子顯微鏡",
                    "LAB A",
                    "故障中",
                    ["表面形貌分析", "材料成份分析"],
                    72,
                    "林育誠",
                    "2026-05-02",
                ),
                (
                    "OPT-001",
                    "光學量測平台",
                    "LAB C",
                    "閒置",
                    ["光學量測", "膜厚量測"],
                    22,
                    "林育誠",
                    "2026-05-12",
                ),
            ],
        )

    recipe_count = conn.execute("SELECT COUNT(*) AS count FROM recipes").fetchone()["count"]
    if recipe_count == 0:
        execute_many(
            conn,
            """
            INSERT INTO recipes (
                recipe_id, name, version, experiment_item, machine_ids,
                method, parameters, updated_by, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [
                (
                    "RCP-TEM-001",
                    "TEM 材料成份標準流程",
                    "v1.0",
                    "材料成份分析",
                    ["TEM-001"],
                    "低劑量成像與 EDS mapping",
                    Jsonb({"voltage": "200kV", "duration": "45min"}),
                    "林育誠",
                    datetime.now(),
                ),
                (
                    "RCP-XRD-001",
                    "XRD 薄膜應力標準流程",
                    "v1.0",
                    "薄膜應力分析",
                    ["XRD-002"],
                    "Omega-2Theta scan",
                    Jsonb({"range": "20-80deg", "step": "0.02deg"}),
                    "陳雅婷",
                    datetime.now(),
                ),
                (
                    "RCP-OPT-001",
                    "光學量測標準流程",
                    "v1.0",
                    "光學量測",
                    ["OPT-001"],
                    "多點反射率快速量測",
                    Jsonb({"points": "9", "duration": "20min"}),
                    "林育誠",
                    datetime.now(),
                ),
            ],
        )

    dispatch_count = conn.execute("SELECT COUNT(*) AS count FROM dispatches").fetchone()[
        "count"
    ]
    if dispatch_count == 0:
        execute_many(
            conn,
            """
            INSERT INTO dispatches (
                dispatch_id, wip_id, order_id, experiment_item,
                priority, lab, due_at, status, created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, '待派工', %s)
            """,
            [
                (
                    "DSP-001",
                    "WIP-001",
                    "WO-001",
                    "材料成份分析",
                    "特急",
                    "LAB A",
                    "2026-05-22 18:00",
                    "王建國",
                ),
                (
                    "DSP-002",
                    "WIP-002",
                    "WO-002",
                    "薄膜應力分析",
                    "高",
                    "LAB B",
                    "2026-05-23 10:00",
                    "王建國",
                ),
                (
                    "DSP-003",
                    "WIP-003",
                    "WO-003",
                    "表面形貌分析",
                    "一般",
                    "LAB A",
                    "2026-05-23 17:00",
                    "王建國",
                ),
                (
                    "DSP-004",
                    "WIP-004",
                    "WO-004",
                    "光學量測",
                    "一般",
                    "LAB C",
                    "2026-05-22 09:00",
                    "王建國",
                ),
                (
                    "DSP-005",
                    "WIP-005",
                    "WO-005",
                    "薄膜應力分析",
                    "特急",
                    "LAB B",
                    "2026-05-24 16:00",
                    "王建國",
                ),
            ],
        )


@app.on_event("startup")
def startup() -> None:
    for attempt in range(1, 21):
        try:
            init_db()
            return
        except psycopg.OperationalError:
            if attempt == 20:
                raise
            time.sleep(0.5)


@app.get("/health")
def health_check() -> dict[str, str]:
    with get_connection() as conn:
        conn.execute("SELECT 1")
    return {"status": "ok", "database": "connected"}


@app.get("/api/users")
def get_users() -> dict[str, object]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM users ORDER BY user_id").fetchall()
    return list_response([user_from_row(row) for row in rows])


@app.get("/api/dashboard")
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
    blocked = sum(1 for row in machines if row["status"] in ["故障中", "保養中", "停用"])
    avg_utilization = round(
        sum(int(row["utilization"]) for row in machines) / len(machines)
    ) if machines else 0

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


@app.get("/api/machines")
def get_machines(x_user_id: str | None = Header(default=None)) -> dict[str, object]:
    with get_connection() as conn:
        user = get_user(conn, x_user_id)
        filter_sql, params = lab_filter_sql(user)
        rows = conn.execute(
            f"SELECT * FROM machines{filter_sql} ORDER BY machine_id",
            params,
        ).fetchall()
    return list_response([machine_from_row(row) for row in rows])


@app.post("/api/machines")
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
            raise HTTPException(status_code=409, detail="Machine already exists") from exc
    return response(machine_from_row(row), "machine created")


@app.patch("/api/machines/{machine_id}/status")
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


@app.patch("/api/machines/{machine_id}")
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


@app.get("/api/recipes")
def get_recipes(x_user_id: str | None = Header(default=None)) -> dict[str, object]:
    with get_connection() as conn:
        user = get_user(conn, x_user_id)
        if can_view_all_labs(user):
            rows = conn.execute("SELECT * FROM recipes ORDER BY updated_at DESC").fetchall()
        else:
            rows = conn.execute(
                """
                SELECT DISTINCT recipes.*
                FROM recipes
                JOIN machines ON machines.machine_id = ANY(recipes.machine_ids)
                WHERE machines.lab = %s
                ORDER BY updated_at DESC
                """,
                (require_lab_scope(user),),
            ).fetchall()
    return list_response([recipe_from_row(row) for row in rows])


@app.post("/api/recipes")
def create_recipe(
    payload: RecipeCreate, x_user_id: str | None = Header(default=None)
) -> dict[str, object]:
    with get_connection() as conn:
        user = get_user(conn, x_user_id)
        require_role(user, {"實驗室人員", "實驗室小主管"})
        machine_count = conn.execute(
            """
            SELECT COUNT(*) AS count
            FROM machines
            WHERE machine_id = ANY(%s)
              AND lab = %s
            """,
            (payload.machineIds, require_lab_scope(user)),
        ).fetchone()["count"]
        if machine_count != len(payload.machineIds):
            raise HTTPException(status_code=400, detail="Some machines do not exist")

        try:
            row = conn.execute(
                """
                INSERT INTO recipes (
                    recipe_id, name, version, experiment_item, machine_ids,
                    method, parameters, updated_by, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    payload.recipeId,
                    payload.name,
                    payload.version,
                    payload.experimentItem,
                    payload.machineIds,
                    payload.method,
                    Jsonb(payload.parameters),
                    user.name,
                    datetime.now(),
                ),
            ).fetchone()
        except psycopg.errors.UniqueViolation as exc:
            raise HTTPException(status_code=409, detail="Recipe already exists") from exc
    return response(recipe_from_row(row), "recipe created")


@app.get("/api/dispatches")
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


@app.post("/api/dispatches")
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
            raise HTTPException(status_code=409, detail="Dispatch already exists") from exc
    return response(dispatch_from_row(row), "dispatch created")


@app.post("/api/dispatches/suggest")
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


@app.post("/api/dispatches/replan")
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


@app.post("/api/dispatches/{dispatch_id}/assign")
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
            raise HTTPException(status_code=400, detail="Dispatch and machine are in different labs")
        if machine["status"] in ["故障中", "保養中", "停用"]:
            raise HTTPException(status_code=400, detail="Machine is not assignable")
        if dispatch["experiment_item"] not in machine["supported_items"]:
            raise HTTPException(status_code=400, detail="Machine does not support this item")
        if payload.machineId not in recipe["machine_ids"]:
            raise HTTPException(status_code=400, detail="Recipe is not available for machine")
        if recipe["experiment_item"] != dispatch["experiment_item"]:
            raise HTTPException(status_code=400, detail="Recipe does not match WIP item")

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

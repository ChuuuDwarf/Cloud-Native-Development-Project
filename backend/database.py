import os
from datetime import datetime
from typing import Any, Sequence

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://lims:lims@127.0.0.1:5432/lims")


def get_connection() -> Any:
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def execute_many(conn: Any, query: str, values: Sequence[tuple[object, ...]]) -> None:
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
        conn.execute(
            "ALTER TABLE dispatches ADD COLUMN IF NOT EXISTS replan_reason TEXT"
        )
        conn.execute(
            "ALTER TABLE dispatches ADD COLUMN IF NOT EXISTS lab TEXT DEFAULT 'LAB A'"
        )
        conn.execute("UPDATE dispatches SET lab = 'LAB A' WHERE lab IS NULL")
        conn.execute("ALTER TABLE dispatches ALTER COLUMN lab SET NOT NULL")
        seed_db(conn)


def seed_db(conn: Any) -> None:
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

    machine_count = conn.execute("SELECT COUNT(*) AS count FROM machines").fetchone()[
        "count"
    ]
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

    recipe_count = conn.execute("SELECT COUNT(*) AS count FROM recipes").fetchone()[
        "count"
    ]
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

    dispatch_count = conn.execute(
        "SELECT COUNT(*) AS count FROM dispatches"
    ).fetchone()["count"]
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

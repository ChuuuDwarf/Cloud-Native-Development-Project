"""API route + database integration tests for Sample/WIP/Transfer flows.

這份測試用 FastAPI TestClient 打真正 API route，並用 SQLite in-memory DB 驗證資料狀態。
重點是功能流程，不檢查 code quality。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sqlalchemy = pytest.importorskip("sqlalchemy")
pytest.importorskip("fastapi.testclient")

from fastapi import Request  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import app.core.database as db_module  # noqa: E402
import app.main  # noqa: E402
import app.routes.samples as samples_route  # noqa: E402
import app.routes.transfers as transfers_route  # noqa: E402
import app.routes.wips as wips_route  # noqa: E402
from app.common.dependencies import CurrentUser, get_current_user  # noqa: E402

app = app.main.app

LAB_A_HEADERS = {"x-user-id": "user-laba-001"}
LAB_B_HEADERS = {"x-user-id": "user-labb-001"}
FACTORY_HEADERS = {"x-user-id": "user-factory-001"}
ADMIN_HEADERS = {"x-user-id": "user-admin-001"}

USER_UUIDS = {
    "user-laba-001": "11111111-aaaa-aaaa-aaaa-111111111111",
    "user-labb-001": "22222222-bbbb-bbbb-bbbb-222222222222",
    "user-factory-001": "33333333-ffff-ffff-ffff-333333333333",
    "user-admin-001": "44444444-adad-adad-adad-444444444444",
}

USER_CONTEXTS = {
    USER_UUIDS["user-laba-001"]: {
        "id": USER_UUIDS["user-laba-001"],
        "name": "張志明",
        "role": "lab_engineer",
        "role_name": "實驗室人員",
        "department": "Lab A",
        "lab_name": "Lab A",
        "email": "laba@example.com",
    },
    USER_UUIDS["user-labb-001"]: {
        "id": USER_UUIDS["user-labb-001"],
        "name": "林雅婷",
        "role": "lab_engineer",
        "role_name": "實驗室人員",
        "department": "Lab B",
        "lab_name": "Lab B",
        "email": "labb@example.com",
    },
    USER_UUIDS["user-factory-001"]: {
        "id": USER_UUIDS["user-factory-001"],
        "name": "王建國",
        "role": "plant_user",
        "role_name": "廠區使用者",
        "department": "F12 廠",
        "lab_name": None,
        "email": "factory@example.com",
    },
    USER_UUIDS["user-admin-001"]: {
        "id": USER_UUIDS["user-admin-001"],
        "name": "系統管理員",
        "role": "system_admin",
        "role_name": "系統管理者",
        "department": "",
        "lab_name": None,
        "email": "admin@example.com",
    },
}

SAMPLE_A_ID = "11111111-1111-1111-1111-111111111111"
SAMPLE_B_ID = "22222222-2222-2222-2222-222222222222"
STORAGE_A_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"


class CachedResult:
    def __init__(self, row=None, rows=None):
        self._row = row
        self._rows = rows

    def fetchone(self):
        return self._row

    def fetchall(self):
        if self._rows is not None:
            return self._rows
        return [] if self._row is None else [self._row]


class SQLiteReturningSafeSession(sqlalchemy.orm.Session):
    def execute(self, statement, params=None, *args, **kwargs):
        result = super().execute(statement, params, *args, **kwargs)

        # SQLite 不能在 RETURNING cursor 尚未讀完時 commit。
        # 後端 route 為了相容 PostgreSQL，會先 commit 再 fetchone。
        # integration test 使用 SQLite，所以這裡先把 RETURNING 結果快取起來並關閉 cursor。
        sql = str(statement).upper()
        if "RETURNING" in sql:
            row = result.fetchone()
            result.close()
            return CachedResult(row=row)

        return result


class AsyncSQLiteSessionAdapter:
    """Minimal async facade over the sync SQLite session used by route tests."""

    def __init__(self, session):
        self.session = session

    async def execute(self, *args, **kwargs):
        return self.session.execute(*args, **kwargs)

    async def scalar(self, *args, **kwargs):
        return self.session.scalar(*args, **kwargs)

    async def commit(self):
        self.session.commit()

    async def rollback(self):
        self.session.rollback()

    async def flush(self):
        self.session.flush()

    async def refresh(self, instance):
        self.session.refresh(instance)

    def add(self, instance):
        self.session.add(instance)


def create_schema(db):
    """建立測試用 schema。

    SQLite 不支援 PostgreSQL 的 uuid_generate_v4()/NOW() default 寫法，
    所以 integration test 使用等價的最小 schema。
    """

    statements = [
        """
        CREATE TABLE departments (
            id TEXT PRIMARY KEY,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE labs (
            id TEXT PRIMARY KEY,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            capacity INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE lab_capabilities (
            id TEXT PRIMARY KEY,
            lab_id TEXT NOT NULL,
            experiment_item TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE machines (
            id TEXT PRIMARY KEY,
            machine_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            lab TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT '閒置',
            supported_items TEXT NOT NULL DEFAULT '[]',
            utilization INTEGER NOT NULL DEFAULT 0,
            owner TEXT NOT NULL DEFAULT '',
            last_maintenance TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            order_no TEXT NOT NULL UNIQUE,
            applicant_id TEXT NOT NULL,
            department_id TEXT NOT NULL,
            apply_date TEXT NOT NULL,
            status TEXT NOT NULL,
            priority TEXT NOT NULL DEFAULT 'normal',
            total_items INTEGER NOT NULL DEFAULT 0,
            last_reason TEXT,
            is_deleted INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE order_items (
            id INTEGER PRIMARY KEY,
            order_id INTEGER NOT NULL,
            sample_id TEXT NOT NULL,
            sample_name TEXT,
            lab_id TEXT NOT NULL,
            experiment_id TEXT NOT NULL,
            target_group TEXT NOT NULL DEFAULT 'G1',
            target INTEGER NOT NULL DEFAULT 1,
            dependency_check INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'approved',
            approved_by TEXT,
            approved_at TEXT,
            return_reason TEXT,
            reject_reason TEXT,
            quota_exceeded INTEGER NOT NULL DEFAULT 0,
            quota_override INTEGER NOT NULL DEFAULT 0,
            quota_override_reason TEXT,
            quota_approved_by TEXT,
            quota_approved_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE storage_locations (
            id TEXT PRIMARY KEY,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            lab_name TEXT,
            description TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE samples (
            id TEXT PRIMARY KEY,
            sample_no TEXT NOT NULL UNIQUE,
            order_no TEXT NOT NULL,
            sample_name TEXT,
            experiment_item TEXT,
            applicant_name TEXT,
            applicant_department TEXT,
            status TEXT NOT NULL DEFAULT 'pending_receive',
            current_location TEXT,
            storage_location_id TEXT,
            received_at TEXT,
            received_by TEXT,
            picked_up_at TEXT,
            picked_up_by TEXT,
            note TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE sample_histories (
            id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
            sample_id TEXT NOT NULL,
            action TEXT NOT NULL,
            from_status TEXT,
            to_status TEXT,
            description TEXT,
            operator_name TEXT,
            lab_name TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE transfers (
            id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
            transfer_no TEXT NOT NULL UNIQUE,
            target_type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            order_no TEXT,
            sample_no TEXT,
            wip_no TEXT,
            from_lab TEXT NOT NULL,
            to_lab TEXT NOT NULL,
            handed_by TEXT,
            received_by TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            transferred_at TEXT,
            received_at TEXT,
            note TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE wips (
            id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
            wip_no TEXT NOT NULL UNIQUE,
            sample_id TEXT NOT NULL,
            order_no TEXT NOT NULL,
            lab_name TEXT,
            experiment_item TEXT,
            priority TEXT NOT NULL DEFAULT 'normal',
            status TEXT NOT NULL DEFAULT 'created',
            progress INTEGER NOT NULL DEFAULT 0,
            current_location TEXT,
            scheduled_at TEXT,
            dispatched_at TEXT,
            started_at TEXT,
            completed_at TEXT,
            terminated_at TEXT,
            note TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE wip_histories (
            id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
            wip_id TEXT NOT NULL,
            action TEXT NOT NULL,
            from_status TEXT,
            to_status TEXT,
            description TEXT,
            operator_name TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
    ]

    for statement in statements:
        db.execute(text(statement))

    # route SQL 使用 NOW()，SQLite 測試 DB 補一個同名 function。
    raw_connection = db.connection().connection
    raw_connection.create_function("NOW", 0, lambda: "2026-05-23 00:00:00")


def seed_data(db):
    db.execute(
        text(
            """
            INSERT INTO departments (id, code, name)
            VALUES
                ('dddddddd-aaaa-aaaa-aaaa-dddddddddddd', 'F12', 'F12 廠'),
                ('dddddddd-laba-aaaa-aaaa-dddddddddddd', 'LABA-DEPT', 'Lab A'),
                ('dddddddd-labb-bbbb-bbbb-dddddddddddd', 'LABB-DEPT', 'Lab B')
            """
        )
    )

    db.execute(
        text(
            """
            INSERT INTO labs (id, code, name, capacity)
            VALUES
                ('aaaaaaaa-0000-0000-0000-000000000001', 'A', 'Lab A', 10),
                ('bbbbbbbb-0000-0000-0000-000000000002', 'B', 'Lab B', 10)
            """
        )
    )

    db.execute(
        text(
            """
            INSERT INTO lab_capabilities (id, lab_id, experiment_item)
            VALUES
                (:sem_id, :lab_a_id, :sem_item),
                (:opt_id, :lab_b_id, :opt_item),
                (:edx_id, :lab_a_id, :edx_item)
            """
        ),
        {
            "sem_id": "cap-sem-0000-0000-0000-000000000001",
            "opt_id": "cap-opt-0000-0000-0000-000000000002",
            "edx_id": "cap-edx-0000-0000-0000-000000000003",
            "lab_a_id": "aaaaaaaa-0000-0000-0000-000000000001",
            "lab_b_id": "bbbbbbbb-0000-0000-0000-000000000002",
            "sem_item": "SEM 觀察",
            "opt_item": "光學量測",
            "edx_item": "EDX 分析",
        },
    )

    db.execute(
        text(
            """
            INSERT INTO machines (
                id, machine_id, name, lab, supported_items, utilization
            )
            VALUES
                (:machine_a_id, 'M-A-1', 'SEM Machine', 'A', :machine_a_items, 80),
                (:machine_b_id, 'M-B-1', 'Optical Machine', 'B', :machine_b_items, 20)
            """
        ),
        {
            "machine_a_id": "machine-a-0000-0000-0000-000000000001",
            "machine_b_id": "machine-b-0000-0000-0000-000000000002",
            "machine_a_items": '["SEM 觀察", "EDX 分析"]',
            "machine_b_items": '["光學量測"]',
        },
    )

    db.execute(
        text(
            """
            INSERT INTO storage_locations (id, code, name, lab_name)
            VALUES (:id, 'A-R01-S01', 'Lab A 暫存架 1', 'Lab A')
            """
        ),
        {"id": STORAGE_A_ID},
    )

    db.execute(
        text(
            """
            INSERT INTO samples (
                id, sample_no, order_no, sample_name, experiment_item,
                applicant_name, applicant_department, status, current_location, note
            )
            VALUES
            (
                :sample_a_id,
                'SMP-2026-0001',
                'ORD-2026-0001',
                '跨 Lab 樣品',
                'Lab A:SEM 觀察、Lab B:光學量測',
                '王建國',
                'F12 廠',
                'pending_receive',
                'Lab A 收樣區',
                NULL
            ),
            (
                :sample_b_id,
                'SMP-2026-0002',
                'ORD-2026-0002',
                '別人樣品',
                'Lab B:光學量測',
                '其他使用者',
                'F12 廠',
                'pending_receive',
                'Lab B 收樣區',
                NULL
            )
            """
        ),
        {"sample_a_id": SAMPLE_A_ID, "sample_b_id": SAMPLE_B_ID},
    )


def fetch_one(db, sql, params=None):
    row = db.execute(text(sql), params or {}).fetchone()
    return dict(row._mapping) if row is not None else None


def fetch_all(db, sql, params=None):
    return [dict(row._mapping) for row in db.execute(text(sql), params or {}).fetchall()]


@pytest.fixture
def integration_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    TestingSessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        class_=SQLiteReturningSafeSession,
    )

    db = TestingSessionLocal()
    create_schema(db)
    seed_data(db)
    db.commit()

    try:
        yield db
    finally:
        db.close()
        engine.dispose()


@pytest.fixture
def client(integration_db):
    async_db = AsyncSQLiteSessionAdapter(integration_db)

    async def override_get_db():
        yield async_db

    async def override_get_current_user(request: Request):
        header_user_id = request.headers.get("x-user-id", "user-admin-001")
        user_uuid = USER_UUIDS[header_user_id]
        user = USER_CONTEXTS[user_uuid]
        return CurrentUser(
            id=user_uuid,
            name=user["name"],
            email=user["email"],
            role=user["role"],
            permissions=["*"],
        )

    async def fake_build_current_user(current_user: CurrentUser, db):
        return USER_CONTEXTS[str(current_user.id)]

    original_builders = (
        samples_route.build_current_user,
        wips_route.build_current_user,
        transfers_route.build_current_user,
    )

    samples_route.build_current_user = fake_build_current_user
    wips_route.build_current_user = fake_build_current_user
    transfers_route.build_current_user = fake_build_current_user

    app.dependency_overrides[db_module.get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        (
            samples_route.build_current_user,
            wips_route.build_current_user,
            transfers_route.build_current_user,
        ) = original_builders


def test_samples_route_filters_visibility_and_status(client):
    lab_a_response = client.get("/api/samples", headers=LAB_A_HEADERS)
    assert lab_a_response.status_code == 200
    lab_a_samples = lab_a_response.json()
    assert [sample["sample_no"] for sample in lab_a_samples] == ["SMP-2026-0001"]

    lab_b_response = client.get("/api/samples", headers=LAB_B_HEADERS)
    assert lab_b_response.status_code == 200
    lab_b_samples = lab_b_response.json()
    assert [sample["sample_no"] for sample in lab_b_samples] == ["SMP-2026-0002"]

    status_response = client.get(
        "/api/samples?status=received",
        headers=ADMIN_HEADERS,
    )
    assert status_response.status_code == 200
    assert status_response.json() == []


def test_wip_dependency_next_claims_lowest_utilization_candidate(client, integration_db):
    integration_db.execute(
        text(
            """
            INSERT INTO orders (
                id, order_no, applicant_id, department_id, apply_date, status, priority, total_items
            )
            VALUES (
                99, 'ORD-2026-0001', 'user-factory-001', 'F12',
                '2026-05-23', 'approved', 'normal', 3
            )
            """
        )
    )
    integration_db.execute(
        text(
            """
            INSERT INTO order_items (
                id, order_id, sample_id, sample_name, lab_id, experiment_id,
                target_group, target, dependency_check, status
            )
            VALUES
                (
                    991, 99, 'SMP-2026-0001', '跨 Lab 樣品',
                    'aaaaaaaa-0000-0000-0000-000000000001',
                    'cap-sem-0000-0000-0000-000000000001',
                    'G1', 1, 0, 'approved'
                ),
                (
                    992, 99, 'SMP-2026-0001', '跨 Lab 樣品',
                    'bbbbbbbb-0000-0000-0000-000000000002',
                    'cap-opt-0000-0000-0000-000000000002',
                    'G2', 1, 0, 'approved'
                ),
                (
                    993, 99, 'SMP-2026-0001', '跨 Lab 樣品',
                    'aaaaaaaa-0000-0000-0000-000000000001',
                    'cap-edx-0000-0000-0000-000000000003',
                    'G1', 2, 0, 'approved'
                )
            """
        )
    )
    integration_db.commit()

    first_response = client.post(
        "/api/wips/dependency/next",
        headers=ADMIN_HEADERS,
        json={"sampleId": SAMPLE_A_ID},
    )

    assert first_response.status_code == 200
    first_payload = first_response.json()
    assert first_payload["success"] is True
    assert first_payload["data"]["orderItemId"] == 992
    assert first_payload["data"]["experimentId"] == "cap-opt-0000-0000-0000-000000000002"
    assert first_payload["data"]["experimentName"] == "光學量測"
    assert first_payload["data"]["check"] is True
    assert first_payload["data"]["reason"] == "lowest_machine_utilization"

    claimed_first = fetch_one(
        integration_db,
        "SELECT dependency_check FROM order_items WHERE id = 992",
    )
    assert claimed_first["dependency_check"] == 1

    second_response = client.post(
        "/api/wips/dependency/next",
        headers=ADMIN_HEADERS,
        json={"sampleId": SAMPLE_A_ID},
    )

    assert second_response.status_code == 200
    assert second_response.json()["data"]["orderItemId"] == 991


def test_wip_dependency_next_returns_null_when_done(client, integration_db):
    integration_db.execute(
        text(
            """
            INSERT INTO orders (
                id, order_no, applicant_id, department_id, apply_date, status, priority, total_items
            )
            VALUES (
                100, 'ORD-2026-0001', 'user-factory-001', 'F12',
                '2026-05-23', 'approved', 'normal', 1
            )
            """
        )
    )
    integration_db.execute(
        text(
            """
            INSERT INTO order_items (
                id, order_id, sample_id, sample_name, lab_id, experiment_id,
                target_group, target, dependency_check, status
            )
            VALUES (
                1001, 100, 'SMP-2026-0001', '跨 Lab 樣品',
                'aaaaaaaa-0000-0000-0000-000000000001',
                'cap-sem-0000-0000-0000-000000000001',
                'G1', 1, 1, 'approved'
            )
            """
        )
    )
    integration_db.commit()

    response = client.post(
        "/api/wips/dependency/next",
        headers=ADMIN_HEADERS,
        json={"sampleId": SAMPLE_A_ID},
    )

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "data": None,
        "message": "No pending dependency item",
    }


def test_wip_dependency_next_rejects_missing_sample(client):
    response = client.post(
        "/api/wips/dependency/next",
        headers=ADMIN_HEADERS,
        json={"sampleId": "99999999-9999-9999-9999-999999999999"},
    )

    assert response.status_code == 404


def test_sample_receive_split_and_wip_creation_persist_to_db(client, integration_db):
    receive_response = client.post(
        f"/api/samples/{SAMPLE_A_ID}/actions",
        headers=LAB_A_HEADERS,
        json={"action": "receive"},
    )

    assert receive_response.status_code == 200
    received_sample = receive_response.json()
    assert received_sample["status"] == "received"
    assert received_sample["current_location"] == "Lab A 實驗暫存區"
    assert received_sample["received_by"] == "張志明"

    split_response = client.post(
        f"/api/samples/{SAMPLE_A_ID}/actions",
        headers=LAB_A_HEADERS,
        json={
            "action": "split",
            "wips": [
                {"lab_name": "Lab A", "experiment_item": "SEM 觀察"},
            ],
        },
    )

    assert split_response.status_code == 200
    split_payload = split_response.json()
    assert split_payload["message"] == "Sample split successfully"
    assert split_payload["current_location"] == "Lab A 實驗暫存區"
    assert len(split_payload["created_wips"]) == 1
    assert split_payload["created_wips"][0]["wip_no"] == "WIP-2026-0001-A-01"
    assert all(
        wip["current_location"] == "Lab A 實驗暫存區" for wip in split_payload["created_wips"]
    )

    sample_row = fetch_one(
        integration_db,
        "SELECT status, current_location FROM samples WHERE id = :id",
        {"id": SAMPLE_A_ID},
    )
    assert sample_row == {
        "status": "split",
        "current_location": "Lab A 實驗暫存區",
    }

    histories = fetch_all(
        integration_db,
        """
        SELECT action, to_status, lab_name
        FROM sample_histories
        WHERE sample_id = :id
        ORDER BY created_at
        """,
        {"id": SAMPLE_A_ID},
    )
    assert [history["action"] for history in histories] == ["receive", "split"]

    wip_histories = fetch_all(
        integration_db,
        "SELECT action, to_status FROM wip_histories ORDER BY created_at",
    )
    assert [history["action"] for history in wip_histories] == ["created_from_split"]


def test_wip_actions_update_wip_sample_location_and_history(client, integration_db):
    client.post(
        f"/api/samples/{SAMPLE_A_ID}/actions",
        headers=LAB_A_HEADERS,
        json={"action": "receive"},
    )

    split_response = client.post(
        f"/api/samples/{SAMPLE_A_ID}/actions",
        headers=LAB_A_HEADERS,
        json={
            "action": "split",
            "wips": [
                {
                    "lab_name": "Lab A",
                    "experiment_item": "SEM 觀察",
                }
            ],
        },
    )
    wip_id = split_response.json()["created_wips"][0]["id"]

    start_response = client.post(
        f"/api/wips/{wip_id}/actions",
        headers=LAB_A_HEADERS,
        json={"action": "start"},
    )
    assert start_response.status_code == 200
    assert start_response.json()["status"] == "running"
    assert start_response.json()["current_location"] == "Lab A 機台區"

    sample_after_start = fetch_one(
        integration_db,
        "SELECT current_location FROM samples WHERE id = :id",
        {"id": SAMPLE_A_ID},
    )
    assert sample_after_start["current_location"] == "Lab A 機台區"

    complete_response = client.post(
        f"/api/wips/{wip_id}/actions",
        headers=LAB_A_HEADERS,
        json={"action": "complete"},
    )
    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == "completed"
    assert complete_response.json()["progress"] == 100
    assert complete_response.json()["current_location"] == "Lab A 實驗暫存區"

    history_actions = fetch_all(
        integration_db,
        """
        SELECT action, to_status
        FROM wip_histories
        WHERE wip_id = :wip_id
        ORDER BY created_at
        """,
        {"wip_id": wip_id},
    )
    assert [item["action"] for item in history_actions] == [
        "created_from_split",
        "start",
        "complete",
    ]


def test_transfer_create_send_and_receive_moves_sample_to_next_lab(
    client,
    integration_db,
):
    client.post(
        f"/api/samples/{SAMPLE_A_ID}/actions",
        headers=LAB_A_HEADERS,
        json={"action": "receive"},
    )

    client.post(
        f"/api/samples/{SAMPLE_A_ID}/actions",
        headers=LAB_A_HEADERS,
        json={
            "action": "split",
            "wips": [
                {"lab_name": "Lab A", "experiment_item": "SEM 觀察"},
            ],
        },
    )

    create_transfer_response = client.post(
        "/api/transfers",
        headers=LAB_A_HEADERS,
        json={
            "target_type": "sample",
            "target_id": SAMPLE_A_ID,
            "from_lab": "Lab A",
            "to_lab": "Lab B",
            "note": "交給 Lab B 做光學量測",
        },
    )

    assert create_transfer_response.status_code == 200
    transfer = create_transfer_response.json()
    assert transfer["status"] == "pending"
    assert transfer["from_lab"] == "Lab A"
    assert transfer["to_lab"] == "Lab B"

    sample_waiting = fetch_one(
        integration_db,
        "SELECT current_location FROM samples WHERE id = :id",
        {"id": SAMPLE_A_ID},
    )
    assert sample_waiting["current_location"] == "Lab A 交接待送區"

    send_response = client.post(
        f"/api/transfers/{transfer['id']}/actions",
        headers=LAB_A_HEADERS,
        json={"action": "send"},
    )
    assert send_response.status_code == 200
    assert send_response.json()["status"] == "transferring"
    assert send_response.json()["next_location"] == "Lab B 收樣區"

    receive_response = client.post(
        f"/api/samples/{SAMPLE_A_ID}/actions",
        headers=LAB_B_HEADERS,
        json={"action": "receive"},
    )
    assert receive_response.status_code == 200
    assert receive_response.json()["status"] == "received"
    assert receive_response.json()["current_location"] == "Lab B 實驗暫存區"

    transfer_after_receive = fetch_one(
        integration_db,
        "SELECT status, received_by FROM transfers WHERE id = :id",
        {"id": transfer["id"]},
    )
    assert transfer_after_receive == {
        "status": "received",
        "received_by": "林雅婷",
    }

    histories = fetch_all(
        integration_db,
        """
        SELECT action, lab_name
        FROM sample_histories
        WHERE sample_id = :id
        ORDER BY created_at
        """,
        {"id": SAMPLE_A_ID},
    )
    history_actions = [history["action"] for history in histories]

    assert "transfer_created" in history_actions
    assert "transfer_sent_to_next_lab_receive_area" in history_actions
    assert "transfer_received_by_next_lab" in history_actions


def test_outbound_and_factory_pickup_complete_full_sample_lifecycle(
    client,
    integration_db,
):
    # 這個測試要驗證「最後一個 Lab 完成後通知廠區取回」。
    # seed_data 預設是 Lab A + Lab B 跨 Lab 樣品，會被後端判斷還需要交接 Lab B。
    # 所以這裡先把測試資料改成只有 Lab A，避免 outbound 被正確擋下。
    integration_db.execute(
        text(
            """
            UPDATE samples
            SET experiment_item = 'Lab A:SEM 觀察'
            WHERE id = :sample_id
            """
        ),
        {"sample_id": SAMPLE_A_ID},
    )
    integration_db.commit()

    receive_response = client.post(
        f"/api/samples/{SAMPLE_A_ID}/actions",
        headers=LAB_A_HEADERS,
        json={"action": "receive"},
    )
    assert receive_response.status_code == 200

    split_response = client.post(
        f"/api/samples/{SAMPLE_A_ID}/actions",
        headers=LAB_A_HEADERS,
        json={
            "action": "split",
            "wips": [
                {
                    "lab_name": "Lab A",
                    "experiment_item": "SEM 觀察",
                }
            ],
        },
    )

    assert split_response.status_code == 200
    wip_id = split_response.json()["created_wips"][0]["id"]

    complete_response = client.post(
        f"/api/wips/{wip_id}/actions",
        headers=LAB_A_HEADERS,
        json={"action": "complete"},
    )

    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == "completed"
    assert complete_response.json()["progress"] == 100

    implicit_outbound_response = client.post(
        f"/api/samples/{SAMPLE_A_ID}/actions",
        headers=LAB_A_HEADERS,
        json={
            "action": "outbound",
            "note": "隱性流程不應通知取回",
        },
    )

    assert implicit_outbound_response.status_code == 400
    assert "通知取件必須由使用者明確確認" in implicit_outbound_response.json()["detail"]

    outbound_response = client.post(
        f"/api/samples/{SAMPLE_A_ID}/actions",
        headers=LAB_A_HEADERS,
        json={
            "action": "outbound",
            "note": "通知廠區取回",
            "confirm_notify_pickup": True,
        },
    )

    assert outbound_response.status_code == 200, outbound_response.json()
    assert outbound_response.json()["status"] == "outbound"
    assert outbound_response.json()["current_location"] == "Lab A 待取件區"

    pickup_response = client.post(
        f"/api/samples/{SAMPLE_A_ID}/actions",
        headers=FACTORY_HEADERS,
        json={"action": "pickup_confirmed"},
    )
    assert pickup_response.status_code == 200
    assert pickup_response.json()["status"] == "picked_up"
    assert pickup_response.json()["current_location"] == "已由使用者取回"
    assert pickup_response.json()["picked_up_by"] == "王建國"

    sample_row = fetch_one(
        integration_db,
        """
        SELECT status, current_location, picked_up_by
        FROM samples
        WHERE id = :id
        """,
        {"id": SAMPLE_A_ID},
    )
    assert sample_row == {
        "status": "picked_up",
        "current_location": "已由使用者取回",
        "picked_up_by": "王建國",
    }

    wip_location = fetch_one(
        integration_db,
        "SELECT current_location FROM wips WHERE sample_id = :id",
        {"id": SAMPLE_A_ID},
    )
    assert wip_location["current_location"] == "已由使用者取回"


def test_route_permissions_and_validation_errors(client):
    factory_receive_response = client.post(
        f"/api/samples/{SAMPLE_A_ID}/actions",
        headers=FACTORY_HEADERS,
        json={"action": "receive"},
    )
    assert factory_receive_response.status_code == 403

    invalid_action_response = client.post(
        f"/api/samples/{SAMPLE_A_ID}/actions",
        headers=LAB_A_HEADERS,
        json={"action": "unknown"},
    )
    assert invalid_action_response.status_code == 400

    missing_wips_response = client.post(
        f"/api/samples/{SAMPLE_A_ID}/actions",
        headers=LAB_A_HEADERS,
        json={
            "action": "split",
            "wips": [],
        },
    )
    assert missing_wips_response.status_code == 400

    factory_transfer_response = client.post(
        "/api/transfers",
        headers=FACTORY_HEADERS,
        json={
            "target_type": "sample",
            "target_id": SAMPLE_A_ID,
            "from_lab": "Lab A",
            "to_lab": "Lab B",
        },
    )
    assert factory_transfer_response.status_code == 403

    invalid_transfer_target_response = client.post(
        "/api/transfers",
        headers=LAB_A_HEADERS,
        json={
            "target_type": "sample",
            "target_id": "not-a-uuid",
            "from_lab": "Lab A",
            "to_lab": "Lab B",
        },
    )
    assert invalid_transfer_target_response.status_code == 400

    lab_b_transfer_a_sample_response = client.post(
        "/api/transfers",
        headers=LAB_B_HEADERS,
        json={
            "target_type": "sample",
            "target_id": SAMPLE_A_ID,
            "from_lab": "Lab B",
            "to_lab": "Lab A",
        },
    )
    assert lab_b_transfer_a_sample_response.status_code == 403


def test_sample_detail_patch_inbound_and_history_routes(client, integration_db):
    detail_response = client.get(
        f"/api/samples/{SAMPLE_A_ID}",
        headers=LAB_A_HEADERS,
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["sample_no"] == "SMP-2026-0001"

    forbidden_detail_response = client.get(
        f"/api/samples/{SAMPLE_B_ID}",
        headers=LAB_A_HEADERS,
    )
    assert forbidden_detail_response.status_code == 403

    patch_response = client.patch(
        f"/api/samples/{SAMPLE_A_ID}",
        headers=LAB_A_HEADERS,
        json={
            "sample_name": "更新後樣品名稱",
            "experiment_item": "Lab A:SEM 觀察",
            "current_location": "Lab A 暫存區",
            "note": "更新備註",
        },
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["sample_name"] == "更新後樣品名稱"
    assert patch_response.json()["experiment_item"] == "Lab A:SEM 觀察"
    assert patch_response.json()["current_location"] == "Lab A 暫存區"
    assert patch_response.json()["note"] == "更新備註"

    receive_response = client.post(
        f"/api/samples/{SAMPLE_A_ID}/actions",
        headers=LAB_A_HEADERS,
        json={
            "action": "receive",
            "current_location": "Lab A 收樣完成區",
        },
    )
    assert receive_response.status_code == 200
    assert receive_response.json()["status"] == "received"
    assert receive_response.json()["current_location"] == "Lab A 收樣完成區"

    inbound_response = client.post(
        f"/api/samples/{SAMPLE_A_ID}/actions",
        headers=LAB_A_HEADERS,
        json={
            "action": "inbound",
            "storage_location_id": STORAGE_A_ID,
            "current_location": "Lab A 暫存架 1",
        },
    )
    assert inbound_response.status_code == 200
    assert inbound_response.json()["status"] == "in_storage"
    assert inbound_response.json()["storage_location_id"] == STORAGE_A_ID
    assert inbound_response.json()["current_location"] == "Lab A 暫存架 1"

    invalid_inbound_response = client.post(
        f"/api/samples/{SAMPLE_B_ID}/actions",
        headers=LAB_B_HEADERS,
        json={
            "action": "inbound",
            "storage_location_id": "not-a-uuid",
        },
    )
    assert invalid_inbound_response.status_code == 400

    history_response = client.get(
        f"/api/samples/{SAMPLE_A_ID}/history",
        headers=LAB_A_HEADERS,
    )
    assert history_response.status_code == 200
    history_actions = [item["action"] for item in history_response.json()]
    assert "receive" in history_actions
    assert "inbound" in history_actions

    admin_history_response = client.get(
        f"/api/samples/{SAMPLE_A_ID}/history",
        headers=ADMIN_HEADERS,
    )
    assert admin_history_response.status_code == 200
    assert len(admin_history_response.json()) >= 2


def test_wip_list_detail_patch_history_and_all_actions(client, integration_db):
    client.post(
        f"/api/samples/{SAMPLE_A_ID}/actions",
        headers=LAB_A_HEADERS,
        json={"action": "receive"},
    )

    split_response = client.post(
        f"/api/samples/{SAMPLE_A_ID}/actions",
        headers=LAB_A_HEADERS,
        json={
            "action": "split",
            "wips": [
                {
                    "lab_name": "Lab A",
                    "experiment_item": "SEM 觀察",
                    "priority": "high",
                },
            ],
        },
    )
    assert split_response.status_code == 200

    created_wips = split_response.json()["created_wips"]
    lab_a_wip = created_wips[0]
    lab_a_wip_id = lab_a_wip["id"]

    # 目前 API 會依流程順序只建立當前 Lab segment 的 WIP。
    # 這裡手動塞一筆 Lab B WIP，讓 list/detail/permission route 可以測跨 Lab 可視性。
    lab_b_wip_id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    integration_db.execute(
        text(
            """
            INSERT INTO wips (
                id, wip_no, sample_id, order_no, lab_name, experiment_item,
                priority, status, progress, current_location
            )
            VALUES (
                :id, 'WIP-2026-0001-B-01', :sample_id, 'ORD-2026-0001',
                'Lab B', '光學量測', 'normal', 'created', 0, 'Lab B 實驗暫存區'
            )
            """
        ),
        {"id": lab_b_wip_id, "sample_id": SAMPLE_A_ID},
    )
    integration_db.commit()
    lab_b_wip = {"id": lab_b_wip_id, "wip_no": "WIP-2026-0001-B-01"}

    lab_a_list_response = client.get(
        "/api/wips",
        headers=LAB_A_HEADERS,
    )
    assert lab_a_list_response.status_code == 200
    assert [item["wip_no"] for item in lab_a_list_response.json()] == ["WIP-2026-0001-A-01"]

    lab_b_list_response = client.get(
        "/api/wips",
        headers=LAB_B_HEADERS,
    )
    assert lab_b_list_response.status_code == 200
    assert [item["wip_no"] for item in lab_b_list_response.json()] == ["WIP-2026-0001-B-01"]

    admin_all_response = client.get(
        "/api/wips?include_all_for_flow=true",
        headers=ADMIN_HEADERS,
    )
    assert admin_all_response.status_code == 200
    assert {item["wip_no"] for item in admin_all_response.json()} == {
        "WIP-2026-0001-A-01",
        "WIP-2026-0001-B-01",
    }

    status_filter_response = client.get(
        "/api/wips?status=created",
        headers=ADMIN_HEADERS,
    )
    assert status_filter_response.status_code == 200
    assert len(status_filter_response.json()) == 2

    detail_response = client.get(
        f"/api/wips/{lab_a_wip_id}",
        headers=LAB_A_HEADERS,
    )
    assert detail_response.status_code == 200
    assert detail_response.json()["wip_no"] == "WIP-2026-0001-A-01"

    forbidden_detail_response = client.get(
        f"/api/wips/{lab_b_wip['id']}",
        headers=LAB_A_HEADERS,
    )
    assert forbidden_detail_response.status_code == 403

    patch_response = client.patch(
        f"/api/wips/{lab_a_wip_id}",
        headers=LAB_A_HEADERS,
        json={
            "priority": "urgent",
            "current_location": "Lab A 特急暫存區",
            "note": "改為急件",
        },
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["priority"] == "urgent"
    assert patch_response.json()["current_location"] == "Lab A 特急暫存區"
    assert patch_response.json()["note"] == "改為急件"

    action_expectations = [
        ("send_to_schedule", "waiting_schedule"),
        ("mark_scheduled", "scheduled"),
        ("mark_dispatched", "dispatched"),
        ("start", "running"),
        ("pause", "paused"),
        ("resume", "running"),
        ("complete", "completed"),
    ]

    for action, expected_status in action_expectations:
        response = client.post(
            f"/api/wips/{lab_a_wip_id}/actions",
            headers=LAB_A_HEADERS,
            json={"action": action},
        )
        assert response.status_code == 200
        assert response.json()["status"] == expected_status

    history_response = client.get(
        f"/api/wips/{lab_a_wip_id}/history",
        headers=LAB_A_HEADERS,
    )
    assert history_response.status_code == 200
    history_actions = [item["action"] for item in history_response.json()]
    for expected_action in [
        "created_from_split",
        "send_to_schedule",
        "mark_scheduled",
        "mark_dispatched",
        "start",
        "pause",
        "resume",
        "complete",
    ]:
        assert expected_action in history_actions

    invalid_action_response = client.post(
        f"/api/wips/{lab_a_wip_id}/actions",
        headers=LAB_A_HEADERS,
        json={"action": "unknown"},
    )
    assert invalid_action_response.status_code == 400

    forbidden_action_response = client.post(
        f"/api/wips/{lab_b_wip['id']}/actions",
        headers=LAB_A_HEADERS,
        json={"action": "start"},
    )
    assert forbidden_action_response.status_code == 403


def test_wip_terminate_action_and_forbidden_patch(client):
    client.post(
        f"/api/samples/{SAMPLE_A_ID}/actions",
        headers=LAB_A_HEADERS,
        json={"action": "receive"},
    )

    split_response = client.post(
        f"/api/samples/{SAMPLE_A_ID}/actions",
        headers=LAB_A_HEADERS,
        json={
            "action": "split",
            "wips": [
                {
                    "lab_name": "Lab A",
                    "experiment_item": "SEM 觀察",
                }
            ],
        },
    )
    assert split_response.status_code == 200
    wip_id = split_response.json()["created_wips"][0]["id"]

    forbidden_patch_response = client.patch(
        f"/api/wips/{wip_id}",
        headers=LAB_B_HEADERS,
        json={
            "priority": "urgent",
        },
    )
    assert forbidden_patch_response.status_code == 403

    terminate_response = client.post(
        f"/api/wips/{wip_id}/actions",
        headers=LAB_A_HEADERS,
        json={
            "action": "terminate",
            "description": "測試終止 WIP",
        },
    )
    assert terminate_response.status_code == 200
    assert terminate_response.json()["status"] == "terminated"

    history_response = client.get(
        f"/api/wips/{wip_id}/history",
        headers=LAB_A_HEADERS,
    )
    assert history_response.status_code == 200
    assert "terminate" in [item["action"] for item in history_response.json()]


def test_transfer_list_duplicate_cancel_and_wip_transfer_routes(client, integration_db):
    client.post(
        f"/api/samples/{SAMPLE_A_ID}/actions",
        headers=LAB_A_HEADERS,
        json={"action": "receive"},
    )

    split_response = client.post(
        f"/api/samples/{SAMPLE_A_ID}/actions",
        headers=LAB_A_HEADERS,
        json={
            "action": "split",
            "wips": [
                {
                    "lab_name": "Lab A",
                    "experiment_item": "SEM 觀察",
                }
            ],
        },
    )
    assert split_response.status_code == 200
    wip_id = split_response.json()["created_wips"][0]["id"]

    create_sample_transfer_response = client.post(
        "/api/transfers",
        headers=LAB_A_HEADERS,
        json={
            "target_type": "sample",
            "target_id": SAMPLE_A_ID,
            "from_lab": "Lab A",
            "to_lab": "Lab B",
            "note": "建立後測試取消",
        },
    )
    assert create_sample_transfer_response.status_code == 200
    sample_transfer = create_sample_transfer_response.json()
    assert sample_transfer["status"] == "pending"

    duplicate_transfer_response = client.post(
        "/api/transfers",
        headers=LAB_A_HEADERS,
        json={
            "target_type": "sample",
            "target_id": SAMPLE_A_ID,
            "from_lab": "Lab A",
            "to_lab": "Lab B",
        },
    )
    assert duplicate_transfer_response.status_code == 409

    lab_a_list_response = client.get(
        "/api/transfers",
        headers=LAB_A_HEADERS,
    )
    assert lab_a_list_response.status_code == 200
    assert any(
        item["transfer_no"] == sample_transfer["transfer_no"] for item in lab_a_list_response.json()
    )

    lab_b_list_response = client.get(
        "/api/transfers",
        headers=LAB_B_HEADERS,
    )
    assert lab_b_list_response.status_code == 200
    assert any(
        item["transfer_no"] == sample_transfer["transfer_no"] for item in lab_b_list_response.json()
    )

    invalid_transfer_action_response = client.post(
        f"/api/transfers/{sample_transfer['id']}/actions",
        headers=LAB_A_HEADERS,
        json={"action": "unknown"},
    )
    assert invalid_transfer_action_response.status_code == 400

    forbidden_transfer_action_response = client.post(
        f"/api/transfers/{sample_transfer['id']}/actions",
        headers=LAB_B_HEADERS,
        json={"action": "send"},
    )
    assert forbidden_transfer_action_response.status_code == 403

    cancel_response = client.post(
        f"/api/transfers/{sample_transfer['id']}/actions",
        headers=LAB_A_HEADERS,
        json={"action": "cancel"},
    )
    assert cancel_response.status_code == 200
    assert cancel_response.json()["message"] == "Transfer cancelled successfully"

    transfer_after_cancel = fetch_one(
        integration_db,
        "SELECT status FROM transfers WHERE id = :id",
        {"id": sample_transfer["id"]},
    )
    assert transfer_after_cancel["status"] == "cancelled"

    cancel_again_response = client.post(
        f"/api/transfers/{sample_transfer['id']}/actions",
        headers=LAB_A_HEADERS,
        json={"action": "cancel"},
    )
    assert cancel_again_response.status_code == 400

    create_wip_transfer_response = client.post(
        "/api/transfers",
        headers=LAB_A_HEADERS,
        json={
            "target_type": "wip",
            "target_id": wip_id,
            "from_lab": "Lab A",
            "to_lab": "Lab B",
            "note": "WIP 交接測試",
        },
    )
    assert create_wip_transfer_response.status_code == 200
    wip_transfer = create_wip_transfer_response.json()
    assert wip_transfer["target_type"] == "wip"
    assert wip_transfer["wip_no"] == "WIP-2026-0001-A-01"
    assert wip_transfer["status"] == "pending"

    wip_waiting_location = fetch_one(
        integration_db,
        "SELECT current_location FROM wips WHERE id = :id",
        {"id": wip_id},
    )
    assert wip_waiting_location["current_location"] == "Lab A 交接待送區"

    send_wip_transfer_response = client.post(
        f"/api/transfers/{wip_transfer['id']}/actions",
        headers=LAB_A_HEADERS,
        json={"action": "send"},
    )
    assert send_wip_transfer_response.status_code == 200
    assert send_wip_transfer_response.json()["status"] == "transferring"
    assert send_wip_transfer_response.json()["next_location"] == "Lab B 收樣區"

    wip_after_send = fetch_one(
        integration_db,
        "SELECT current_location FROM wips WHERE id = :id",
        {"id": wip_id},
    )
    assert wip_after_send["current_location"] == "Lab B 收樣區"

    wip_history_actions = fetch_all(
        integration_db,
        """
        SELECT action
        FROM wip_histories
        WHERE wip_id = :wip_id
        ORDER BY created_at
        """,
        {"wip_id": wip_id},
    )
    assert "transfer_created" in [item["action"] for item in wip_history_actions]
    assert "transfer_sent_to_next_lab_receive_area" in [
        item["action"] for item in wip_history_actions
    ]


def test_transfer_create_validation_branches(client):
    invalid_target_type_response = client.post(
        "/api/transfers",
        headers=LAB_A_HEADERS,
        json={
            "target_type": "bad",
            "target_id": SAMPLE_A_ID,
            "from_lab": "Lab A",
            "to_lab": "Lab B",
        },
    )
    assert invalid_target_type_response.status_code == 400

    missing_to_lab_response = client.post(
        "/api/transfers",
        headers=LAB_A_HEADERS,
        json={
            "target_type": "sample",
            "target_id": SAMPLE_A_ID,
            "from_lab": "Lab A",
        },
    )
    assert missing_to_lab_response.status_code == 400

    same_lab_response = client.post(
        "/api/transfers",
        headers=LAB_A_HEADERS,
        json={
            "target_type": "sample",
            "target_id": SAMPLE_A_ID,
            "from_lab": "Lab A",
            "to_lab": "Lab A",
        },
    )
    assert same_lab_response.status_code == 400

    not_found_response = client.post(
        "/api/transfers",
        headers=LAB_A_HEADERS,
        json={
            "target_type": "sample",
            "target_id": "99999999-9999-9999-9999-999999999999",
            "from_lab": "Lab A",
            "to_lab": "Lab B",
        },
    )
    assert not_found_response.status_code == 404


def test_outbound_is_blocked_by_pending_transfer_and_incomplete_wip(client):
    client.post(
        f"/api/samples/{SAMPLE_A_ID}/actions",
        headers=LAB_A_HEADERS,
        json={"action": "receive"},
    )

    split_response = client.post(
        f"/api/samples/{SAMPLE_A_ID}/actions",
        headers=LAB_A_HEADERS,
        json={
            "action": "split",
            "wips": [
                {
                    "lab_name": "Lab A",
                    "experiment_item": "SEM 觀察",
                }
            ],
        },
    )
    assert split_response.status_code == 200
    wip_id = split_response.json()["created_wips"][0]["id"]

    incomplete_outbound_response = client.post(
        f"/api/samples/{SAMPLE_A_ID}/actions",
        headers=LAB_A_HEADERS,
        json={"action": "outbound"},
    )
    assert incomplete_outbound_response.status_code == 400
    assert "未完成的 WIP" in incomplete_outbound_response.json()["detail"]

    complete_response = client.post(
        f"/api/wips/{wip_id}/actions",
        headers=LAB_A_HEADERS,
        json={"action": "complete"},
    )
    assert complete_response.status_code == 200

    transfer_response = client.post(
        "/api/transfers",
        headers=LAB_A_HEADERS,
        json={
            "target_type": "sample",
            "target_id": SAMPLE_A_ID,
            "from_lab": "Lab A",
            "to_lab": "Lab B",
        },
    )
    assert transfer_response.status_code == 200

    pending_transfer_outbound_response = client.post(
        f"/api/samples/{SAMPLE_A_ID}/actions",
        headers=LAB_A_HEADERS,
        json={"action": "outbound"},
    )
    assert pending_transfer_outbound_response.status_code == 400
    assert "尚未完成的交接流程" in pending_transfer_outbound_response.json()["detail"]

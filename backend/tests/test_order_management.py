import importlib
from unittest.mock import MagicMock
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from main import app


client = TestClient(app)

# ============================================================
# Test Data Isolation
# ============================================================


@pytest.fixture(autouse=True)
def clean_order_related_tables():
    """
    每個測試前後清理 order_management 相關資料，避免：
    - PostgreSQL 測試資料累積
    - quota_usages 累積造成 approve 偶發失敗
    - list/filter 測試被前一次測試資料影響

    注意：
    - 不清 users / departments / labs / experiments / quota_settings
    - 因為那些通常是 seed/master data
    """
    main = importlib.import_module("main")
    engine = getattr(main, "engine", None)

    if engine is None:
        yield
        return

    tables = [
        "order_histories",
        "order_items",
        "orders",
        "quota_usages",
    ]

    def cleanup():
        with engine.begin() as connection:
            for table in tables:
                try:
                    connection.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE"))
                except Exception:
                    # 有些環境可能還沒有某些表，避免測試 collection 直接炸掉
                    pass

    cleanup()
    yield
    cleanup()


# ============================================================
# Common Helpers
# ============================================================


def assert_success(response, expected_status=200):
    assert response.status_code == expected_status, response.text
    payload = response.json()

    # /health 沒有 success 欄位；其他 API 若有 success 才檢查
    if isinstance(payload, dict) and "success" in payload:
        assert payload.get("success") is True, payload

    return payload


def assert_error(response, allowed_statuses=None):
    if allowed_statuses is None:
        assert response.status_code >= 400, response.text
    else:
        assert response.status_code in allowed_statuses, response.text

    try:
        return response.json()
    except Exception:
        return {}


def create_order(
    applicant_id="user001",
    department_id="D001",
    sample_id="S001",
    lab_id="LAB001",
    experiment_id="EXP001",
    priority="normal",
    apply_date=None,
):
    body = {
        "applicantId": applicant_id,
        "departmentId": department_id,
        "priority": priority,
        "items": [
            {
                "sampleId": sample_id,
                "labId": lab_id,
                "experimentId": experiment_id,
            }
        ],
    }

    if apply_date is not None:
        body["applyDate"] = apply_date

    response = client.post("/api/orders", json=body)

    # 建立資源成功時，目前 FastAPI 回 201 Created
    payload = assert_success(response, 201)
    order_id = payload["data"]["id"]

    # create 回傳摘要，後續測試需要完整資料，所以再查 detail
    detail_payload = assert_success(client.get(f"/api/orders/{order_id}"), 200)
    return detail_payload["data"]


def action(order_id, action_name, actor_id="user001", reason=None, quota_override=False):
    body = {
        "action": action_name,
        "actorId": actor_id,
    }

    if reason is not None:
        body["reason"] = reason

    if quota_override:
        body["quotaOverride"] = True

    return client.post(f"/api/orders/{order_id}/actions", json=body)


def get_engine():
    main = importlib.import_module("main")
    engine = getattr(main, "engine", None)

    if engine is None:
        pytest.skip("main.py 沒有匯出 engine，略過 DB engine 測試")

    return engine


def get_session_local():
    main = importlib.import_module("main")
    session_local = getattr(main, "SessionLocal", None)

    if session_local is None:
        pytest.skip("main.py 沒有匯出 SessionLocal，略過 DB session 測試")

    return session_local


# ============================================================
# Basic Health / Master Data
# ============================================================


def test_health_check():
    response = client.get("/health")
    payload = assert_success(response, 200)

    assert payload["status"] == "ok"
    assert payload["service"] == "order-management"


def test_master_data_apis():
    response = client.get("/api/master-data")
    payload = assert_success(response, 200)

    data = payload["data"]
    assert "departments" in data
    assert "labs" in data
    assert "experiments" in data
    assert len(data["departments"]) > 0
    assert len(data["labs"]) > 0
    assert len(data["experiments"]) > 0

    assert_success(client.get("/api/labs"), 200)
    assert_success(client.get("/api/departments"), 200)
    assert_success(client.get("/api/experiments"), 200)
    assert_success(client.get("/api/experiments?labId=LAB001"), 200)


def test_quota_and_related_demo_apis():
    assert_success(client.get("/api/samples"), 200)
    assert_success(client.get("/api/wips"), 200)
    assert_success(client.get("/api/reports"), 200)
    assert_success(client.get("/api/issues"), 200)
    assert_success(client.get("/api/quotas"), 200)

    response = client.get("/api/quotas/check?applicantId=user001&departmentId=D001&itemCount=1")
    payload = assert_success(response, 200)

    assert "allowed" in payload["data"]
    assert "needOverride" in payload["data"]


# ============================================================
# Order Core API Tests
# ============================================================


def test_create_get_list_detail_and_history():
    order = create_order(sample_id="S100")
    order_id = order["id"]

    assert order["status"] == "draft"
    assert order["totalItems"] == 1
    assert len(order["items"]) == 1

    list_payload = assert_success(client.get("/api/orders"), 200)
    assert any(item["id"] == order_id for item in list_payload["data"])

    detail_payload = assert_success(client.get(f"/api/orders/{order_id}"), 200)
    assert detail_payload["data"]["id"] == order_id
    assert detail_payload["data"]["orderNo"] == order["orderNo"]

    history_payload = assert_success(client.get(f"/api/orders/{order_id}/history"), 200)
    assert len(history_payload["data"]) >= 1


def test_create_order_accepts_valid_payload():
    order = create_order(sample_id="VAL-001")

    assert order["status"] == "draft"
    assert order["applicantId"] == "user001"
    assert order["departmentId"] == "D001"
    assert order["totalItems"] == 1
    assert len(order["items"]) == 1


def test_apply_date_is_accepted_when_creating_order():
    order = create_order(sample_id="DATE-001", apply_date="2026-05-14")

    assert order["status"] == "draft"
    assert order["orderNo"]


def test_edit_draft_order():
    order = create_order(sample_id="S200")
    order_id = order["id"]

    response = client.patch(
        f"/api/orders/{order_id}",
        json={
            "departmentId": "D002",
            "priority": "urgent",
            "items": [
                {
                    "sampleId": "S201",
                    "labId": "LAB002",
                    "experimentId": "EXP003",
                }
            ],
        },
    )

    payload = assert_success(response, 200)
    data = payload["data"]

    assert data["departmentId"] == "D002"
    assert data["priority"] == "urgent"
    assert data["items"][0]["sampleId"] == "S201"


def test_get_order_list_accepts_page_limit_status_and_applicant_filter():
    order = create_order(applicant_id="user001", sample_id="FILTER-001")

    response = client.get(
        "/api/orders",
        params={
            "page": "1",
            "limit": "50",
            "status": "draft",
            "applicantId": "user001",
        },
    )

    payload = assert_success(response, 200)

    assert isinstance(payload["data"], list)
    assert any(item["id"] == order["id"] for item in payload["data"])


def test_get_order_list_default_query_params_should_work():
    response = client.get("/api/orders")
    payload = assert_success(response, 200)

    assert isinstance(payload["data"], list)


def test_get_orders_by_applicant_api_returns_array():
    order = create_order(applicant_id="user001", sample_id="APP-EXTRA-001")

    response = client.get("/api/orders/applicant/user001")
    payload = assert_success(response, 200)

    assert isinstance(payload["data"], list)
    assert any(item["id"] == order["id"] for item in payload["data"])


def test_create_order_rejects_unknown_applicant():
    response = client.post(
        "/api/orders",
        json={
            "applicantId": "unknown_user",
            "departmentId": "D001",
            "priority": "normal",
            "items": [
                {
                    "sampleId": "UNKNOWN-USER-001",
                    "labId": "LAB001",
                    "experimentId": "EXP001",
                }
            ],
        },
    )

    assert_error(response, allowed_statuses={400, 404, 422})


# ============================================================
# Validation / Error Path Tests
# 對應 orderValidation.test.ts / validate.test.ts / order.test.ts
# ============================================================


def test_create_order_rejects_required_field_missing_cases():
    invalid_payloads = [
        {
            "applicantId": "",
            "departmentId": "D001",
            "items": [
                {
                    "sampleId": "S1",
                    "labId": "LAB001",
                    "experimentId": "EXP001",
                }
            ],
        },
        {
            "applicantId": "user001",
            "departmentId": "",
            "items": [
                {
                    "sampleId": "S1",
                    "labId": "LAB001",
                    "experimentId": "EXP001",
                }
            ],
        },
        {
            "applicantId": "user001",
            "departmentId": "D001",
            "items": [],
        },
        {
            "applicantId": "user001",
            "departmentId": "D001",
            "items": [
                {
                    "sampleId": "",
                    "labId": "LAB001",
                    "experimentId": "EXP001",
                }
            ],
        },
        {
            "applicantId": "user001",
            "departmentId": "D001",
            "items": [
                {
                    "sampleId": "S1",
                    "labId": "",
                    "experimentId": "EXP001",
                }
            ],
        },
        {
            "applicantId": "user001",
            "departmentId": "D001",
            "items": [
                {
                    "sampleId": "S1",
                    "labId": "LAB001",
                    "experimentId": "",
                }
            ],
        },
    ]

    for payload in invalid_payloads:
        response = client.post("/api/orders", json=payload)
        assert_error(response, allowed_statuses={400, 422})


def test_create_order_rejects_too_many_items():
    many_items = [
        {
            "sampleId": f"S{i:03d}",
            "labId": "LAB001",
            "experimentId": "EXP001",
        }
        for i in range(11)
    ]

    response = client.post(
        "/api/orders",
        json={
            "applicantId": "user001",
            "departmentId": "D001",
            "priority": "normal",
            "items": many_items,
        },
    )

    assert_error(response, allowed_statuses={400, 422})


def test_get_patch_delete_non_existing_order_returns_error():
    not_exist_id = 999999999

    response = client.get(f"/api/orders/{not_exist_id}")
    assert_error(response, allowed_statuses={404})

    response = client.patch(
        f"/api/orders/{not_exist_id}",
        json={
            "departmentId": "D001",
            "priority": "normal",
            "items": [
                {
                    "sampleId": "S1",
                    "labId": "LAB001",
                    "experimentId": "EXP001",
                }
            ],
        },
    )
    assert_error(response, allowed_statuses={404})

    response = client.delete(f"/api/orders/{not_exist_id}")
    assert_error(response, allowed_statuses={404})


def test_malformed_json_returns_validation_error():
    response = client.post(
        "/api/orders",
        content='{ "invalid": json ',
        headers={"Content-Type": "application/json"},
    )

    assert_error(response, allowed_statuses={400, 422})


def test_validation_error_when_body_type_is_invalid():
    response = client.post(
        "/api/orders",
        json={
            "applicantId": "user001",
            "departmentId": "D001",
            "items": "this should be a list",
        },
    )

    assert_error(response, allowed_statuses={400, 422})


def test_validation_error_when_item_is_missing_required_keys():
    response = client.post(
        "/api/orders",
        json={
            "applicantId": "user001",
            "departmentId": "D001",
            "items": [
                {
                    "sampleId": "S1",
                }
            ],
        },
    )

    assert_error(response, allowed_statuses={400, 422})


# ============================================================
# Workflow Tests
# ============================================================


def test_submit_return_edit_resubmit_and_approve_flow():
    order = create_order(sample_id="S300")
    order_id = order["id"]

    response = action(order_id, "submit", actor_id="user001")
    payload = assert_success(response, 200)
    assert payload["data"]["status"] == "pending_approval"

    response = action(order_id, "return", actor_id="manager001")
    assert_error(response)

    response = action(
        order_id,
        "return",
        actor_id="manager001",
        reason="樣品資料需要補件",
    )
    payload = assert_success(response, 200)
    assert payload["data"]["status"] == "returned"

    response = client.patch(
        f"/api/orders/{order_id}",
        json={
            "departmentId": "D001",
            "priority": "normal",
            "items": [
                {
                    "sampleId": "S301",
                    "labId": "LAB001",
                    "experimentId": "EXP002",
                }
            ],
        },
    )
    payload = assert_success(response, 200)
    assert payload["data"]["status"] == "returned"
    assert payload["data"]["items"][0]["sampleId"] == "S301"

    response = action(order_id, "submit", actor_id="user001")
    payload = assert_success(response, 200)
    assert payload["data"]["status"] == "pending_approval"

    response = action(
        order_id,
        "approve",
        actor_id="manager001",
        reason="主管特批超額送測",
        quota_override=True,
    )
    payload = assert_success(response, 200)
    assert payload["data"]["status"] == "approved"


def test_full_order_lifecycle_to_closed():
    order = create_order(sample_id="S400")
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)
    assert_success(
        action(
            order_id,
            "approve",
            actor_id="manager001",
            reason="測試環境配額已滿，使用特批核准",
            quota_override=True,
        ),
        200,
    )

    response = action(order_id, "confirm_delivery", actor_id="user001")
    payload = assert_success(response, 200)
    assert payload["data"]["status"] == "sample_delivered"

    response = action(order_id, "confirm_received", actor_id="labstaff001")
    payload = assert_success(response, 200)
    assert payload["data"]["status"] == "sample_received"

    response = action(order_id, "ready_for_pickup", actor_id="labstaff001")
    payload = assert_success(response, 200)
    assert payload["data"]["status"] == "ready_for_pickup"

    response = action(order_id, "close", actor_id="labstaff001")
    payload = assert_success(response, 200)
    assert payload["data"]["status"] == "closed"

    response = action(
        order_id,
        "return",
        actor_id="manager001",
        reason="已結案不應可退回",
    )
    assert_error(response)

    response = action(
        order_id,
        "reject",
        actor_id="manager001",
        reason="已結案不應可拒絕",
    )
    assert_error(response)


def test_reject_requires_reason_and_rejected_is_final():
    order = create_order(sample_id="S500")
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    response = action(order_id, "reject", actor_id="manager001")
    assert_error(response)

    response = action(
        order_id,
        "reject",
        actor_id="manager001",
        reason="不符合送測條件",
    )
    payload = assert_success(response, 200)
    assert payload["data"]["status"] == "rejected"

    response = action(order_id, "submit", actor_id="user001")
    assert_error(response)

    response = action(order_id, "approve", actor_id="manager001")
    assert_error(response)

    history_payload = assert_success(client.get(f"/api/orders/{order_id}/history"), 200)
    assert any(item["action"] == "reject" and item.get("reason") == "不符合送測條件" for item in history_payload["data"])


def test_cancel_flow():
    draft_order = create_order(sample_id="S600")
    draft_order_id = draft_order["id"]

    response = action(draft_order_id, "cancel", actor_id="user001")
    payload = assert_success(response, 200)
    assert payload["data"]["status"] == "cancelled"

    response = action(draft_order_id, "submit", actor_id="user001")
    assert_error(response)

    pending_order = create_order(sample_id="S601")
    pending_order_id = pending_order["id"]

    assert_success(action(pending_order_id, "submit", actor_id="user001"), 200)

    response = action(pending_order_id, "cancel", actor_id="user001")
    payload = assert_success(response, 200)
    assert payload["data"]["status"] == "cancelled"


def test_delete_only_draft_order():
    draft_order = create_order(sample_id="S700")
    draft_order_id = draft_order["id"]

    response = client.delete(f"/api/orders/{draft_order_id}")
    payload = assert_success(response, 200)
    assert payload["data"]["id"] == draft_order_id

    response = client.get(f"/api/orders/{draft_order_id}")
    assert_error(response)

    submitted_order = create_order(sample_id="S701")
    submitted_order_id = submitted_order["id"]

    assert_success(action(submitted_order_id, "submit", actor_id="user001"), 200)

    response = client.delete(f"/api/orders/{submitted_order_id}")
    assert_error(response)


# ============================================================
# Workflow Guard Tests
# ============================================================


def test_submit_when_status_is_not_draft_or_returned_should_fail():
    order = create_order(sample_id="SUBMIT-BLOCK-001")
    order_id = order["id"]

    response = action(order_id, "cancel", actor_id="user001")
    payload = assert_success(response, 200)
    assert payload["data"]["status"] == "cancelled"

    response = action(order_id, "submit", actor_id="user001")
    assert_error(response, allowed_statuses={400, 409})


def test_approve_draft_order_should_fail():
    order = create_order(sample_id="APPROVE-DRAFT-001")
    order_id = order["id"]

    response = action(order_id, "approve", actor_id="manager001")
    assert_error(response, allowed_statuses={400, 409})


def test_return_and_reject_only_allowed_when_pending_approval():
    order = create_order(sample_id="RETURN-DRAFT-001")
    order_id = order["id"]

    response = action(
        order_id,
        "return",
        actor_id="manager001",
        reason="草稿不應可退回",
    )
    assert_error(response, allowed_statuses={400, 409})

    response = action(
        order_id,
        "reject",
        actor_id="manager001",
        reason="草稿不應可拒絕",
    )
    assert_error(response, allowed_statuses={400, 409})


def test_return_and_reject_reason_required():
    order = create_order(sample_id="REASON-001")
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    response = action(order_id, "return", actor_id="manager001")
    assert_error(response, allowed_statuses={400, 422})

    response = action(order_id, "reject", actor_id="manager001")
    assert_error(response, allowed_statuses={400, 422})


def test_approve_with_quota_override_when_quota_exceeded():
    order = create_order(sample_id="QUOTA-OVERRIDE-001")
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    response = action(order_id, "approve", actor_id="manager001")

    if response.status_code >= 400:
        payload = assert_success(
            action(
                order_id,
                "approve",
                actor_id="manager001",
                reason="超額測試，主管特批",
                quota_override=True,
            ),
            200,
        )
        assert payload["data"]["status"] == "approved"
    else:
        payload = response.json()
        assert payload["data"]["status"] == "approved"


def test_update_not_allowed_after_approved():
    order = create_order(sample_id="UPDATE-BLOCK-001")
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)
    assert_success(
        action(
            order_id,
            "approve",
            actor_id="manager001",
            reason="測試環境配額已滿，使用特批核准",
            quota_override=True,
        ),
        200,
    )

    response = client.patch(
        f"/api/orders/{order_id}",
        json={
            "departmentId": "D002",
            "priority": "urgent",
            "items": [
                {
                    "sampleId": "SHOULD-NOT-UPDATE",
                    "labId": "LAB001",
                    "experimentId": "EXP001",
                }
            ],
        },
    )

    assert_error(response, allowed_statuses={400, 409})


def test_delete_not_allowed_after_submit():
    order = create_order(sample_id="DELETE-BLOCK-001")
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    response = client.delete(f"/api/orders/{order_id}")
    assert_error(response, allowed_statuses={400, 409})


def test_history_records_return_reason():
    order = create_order(sample_id="HISTORY-REASON-001")
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    reason = "補件原因測試"
    assert_success(
        action(order_id, "return", actor_id="manager001", reason=reason),
        200,
    )

    response = client.get(f"/api/orders/{order_id}/history")
    payload = assert_success(response, 200)

    assert any(item.get("action") == "return" and item.get("reason") == reason for item in payload["data"])


# ============================================================
# DB Config / Transaction Tests
# 對應 dbConfig.test.ts、db.transaction.impl.test.ts、
# db.closepool.test.ts、db.failure.test.ts、db.more.test.ts
# ============================================================


def test_database_config_exposes_engine_or_database_url():
    main = importlib.import_module("main")

    engine = getattr(main, "engine", None)
    database_url = getattr(main, "DATABASE_URL", None)

    assert engine is not None or database_url is not None

    if engine is not None:
        assert engine.url.drivername.startswith("postgresql")


def test_database_engine_can_connect_and_execute_select_1():
    engine = get_engine()

    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        assert result.scalar() == 1


def test_session_local_can_open_execute_and_close():
    session_local = get_session_local()

    session = session_local()

    try:
        result = session.execute(text("SELECT 1"))
        assert result.scalar() == 1
    finally:
        session.close()


def test_transaction_commit_persists_data():
    engine = get_engine()

    table_name = "pytest_tx_commit_check"

    with engine.begin() as connection:
        connection.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
        connection.execute(
            text(
                f"""
                CREATE TABLE {table_name} (
                    id SERIAL PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
        )

    with engine.begin() as connection:
        connection.execute(
            text(f"INSERT INTO {table_name} (value) VALUES (:value)"),
            {"value": "committed"},
        )

    with engine.connect() as connection:
        result = connection.execute(
            text(f"SELECT value FROM {table_name} WHERE value = :value"),
            {"value": "committed"},
        )
        assert result.scalar() == "committed"

    with engine.begin() as connection:
        connection.execute(text(f"DROP TABLE IF EXISTS {table_name}"))


def test_transaction_rollback_when_exception_happens():
    engine = get_engine()

    table_name = "pytest_tx_rollback_check"

    with engine.begin() as connection:
        connection.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
        connection.execute(
            text(
                f"""
                CREATE TABLE {table_name} (
                    id SERIAL PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
        )

    with pytest.raises(RuntimeError):
        with engine.begin() as connection:
            connection.execute(
                text(f"INSERT INTO {table_name} (value) VALUES (:value)"),
                {"value": "should_rollback"},
            )
            raise RuntimeError("Force transaction rollback")

    with engine.connect() as connection:
        result = connection.execute(
            text(f"SELECT COUNT(*) FROM {table_name} WHERE value = :value"),
            {"value": "should_rollback"},
        )
        assert result.scalar() == 0

    with engine.begin() as connection:
        connection.execute(text(f"DROP TABLE IF EXISTS {table_name}"))


def test_database_connection_failure_raises_operational_error():
    bad_engine = create_engine(
        "postgresql+psycopg://postgres:postgres@localhost:59999/not_existing_db",
        pool_pre_ping=True,
        connect_args={"connect_timeout": 1},
    )

    with pytest.raises(OperationalError):
        with bad_engine.connect() as connection:
            connection.execute(text("SELECT 1"))


def test_create_database_tables_calls_metadata_create_all(monkeypatch):
    main = importlib.import_module("main")

    create_database_tables = getattr(main, "create_database_tables", None)
    base = getattr(main, "Base", None)
    engine = getattr(main, "engine", None)

    if create_database_tables is None or base is None or engine is None:
        pytest.skip("main.py 沒有 create_database_tables / Base / engine，略過啟動建表測試")

    create_all_mock = MagicMock()

    monkeypatch.setattr(base.metadata, "create_all", create_all_mock)

    create_database_tables()

    create_all_mock.assert_called_once_with(bind=engine)


def test_get_db_dependency_closes_session(monkeypatch):
    main = importlib.import_module("main")
    get_db = getattr(main, "get_db", None)

    if get_db is None:
        pytest.skip("main.py 沒有 get_db dependency，略過 close session 測試")

    fake_session = MagicMock()

    def fake_session_local():
        return fake_session

    if hasattr(main, "SessionLocal"):
        monkeypatch.setattr(main, "SessionLocal", fake_session_local)
    else:
        pytest.skip("main.py 沒有 SessionLocal，略過 close session 測試")

    db_generator = get_db()

    db = next(db_generator)
    assert db is fake_session

    with pytest.raises(StopIteration):
        next(db_generator)

    fake_session.close.assert_called_once()

    # ============================================================


# Extra Quota Boundary Tests
# ============================================================


def approve_with_optional_quota_override(order_id):
    """
    有些測試環境 quota 可能已滿。
    這個 helper 先嘗試一般 approve；
    如果因 quota 失敗，再用 quotaOverride + reason 特批核准。
    """
    response = action(order_id, "approve", actor_id="manager001")

    if response.status_code == 200:
        return assert_success(response, 200)

    return assert_success(
        action(
            order_id,
            "approve",
            actor_id="manager001",
            reason="測試環境配額不足，使用 quotaOverride 特批核准",
            quota_override=True,
        ),
        200,
    )


def test_quota_override_requires_reason():
    order = create_order(sample_id="QUOTA-NO-REASON-001")
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    response = action(
        order_id,
        "approve",
        actor_id="manager001",
        quota_override=True,
    )

    assert_error(response, allowed_statuses={400, 422})


def test_approve_with_quota_override_can_succeed_when_normal_approve_fails():
    order = create_order(sample_id="QUOTA-OVERRIDE-001")
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    normal_response = action(order_id, "approve", actor_id="manager001")

    if normal_response.status_code == 200:
        payload = normal_response.json()
        assert payload["data"]["status"] == "approved"
        return

    assert_error(normal_response, allowed_statuses={400, 409})

    override_payload = assert_success(
        action(
            order_id,
            "approve",
            actor_id="manager001",
            reason="主管特批超額送測",
            quota_override=True,
        ),
        200,
    )

    assert override_payload["data"]["status"] == "approved"


def test_quota_check_api_returns_required_fields():
    response = client.get(
        "/api/quotas/check",
        params={
            "applicantId": "user001",
            "departmentId": "D001",
            "itemCount": 1,
        },
    )

    payload = assert_success(response, 200)
    data = payload["data"]

    assert "allowed" in data
    assert "needOverride" in data
    assert "checks" in data
    assert isinstance(data["checks"], list)
    assert len(data["checks"]) > 0

    for check in data["checks"]:
        assert "allowed" in check
        assert "limit" in check

        # 不同版本可能叫 used / currentUsed / usedCount，所以放寬
        assert "used" in check or "currentUsed" in check or "usedCount" in check or "normalUsed" in check


# ============================================================
# Soft Delete Tests
# ============================================================


def test_deleted_draft_order_should_not_appear_in_order_list():
    order = create_order(sample_id="SOFT-DELETE-001")
    order_id = order["id"]

    delete_payload = assert_success(client.delete(f"/api/orders/{order_id}"), 200)
    assert delete_payload["data"]["id"] == order_id

    list_payload = assert_success(client.get("/api/orders"), 200)

    assert all(item["id"] != order_id for item in list_payload["data"])


def test_deleted_order_cannot_be_patched_or_submitted():
    order = create_order(sample_id="SOFT-DELETE-002")
    order_id = order["id"]

    assert_success(client.delete(f"/api/orders/{order_id}"), 200)

    patch_response = client.patch(
        f"/api/orders/{order_id}",
        json={
            "departmentId": "D001",
            "priority": "normal",
            "items": [
                {
                    "sampleId": "SHOULD-NOT-UPDATE",
                    "labId": "LAB001",
                    "experimentId": "EXP001",
                }
            ],
        },
    )
    assert_error(patch_response, allowed_statuses={400, 404, 409})

    submit_response = action(order_id, "submit", actor_id="user001")
    assert_error(submit_response, allowed_statuses={400, 404, 409})


def test_deleted_order_history_policy_is_consistent():
    """
    這個測試不強迫你一定要保留或隱藏 history。
    只檢查刪除後 history API 不可以 500。
    """
    order = create_order(sample_id="SOFT-DELETE-HISTORY-001")
    order_id = order["id"]

    assert_success(client.delete(f"/api/orders/{order_id}"), 200)

    response = client.get(f"/api/orders/{order_id}/history")

    assert response.status_code in {200, 404}


# ============================================================
# Duplicate / Race Condition Guard Tests
# ============================================================


def test_approve_same_order_twice_should_fail_second_time():
    order = create_order(sample_id="DOUBLE-APPROVE-001")
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    approve_payload = approve_with_optional_quota_override(order_id)
    assert approve_payload["data"]["status"] == "approved"

    second_response = action(order_id, "approve", actor_id="manager001")

    assert_error(second_response, allowed_statuses={400, 409})


def test_reject_after_approve_should_fail():
    order = create_order(sample_id="REJECT-AFTER-APPROVE-001")
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    approve_payload = approve_with_optional_quota_override(order_id)
    assert approve_payload["data"]["status"] == "approved"

    reject_response = action(
        order_id,
        "reject",
        actor_id="manager001",
        reason="已核准後不應可拒絕",
    )

    assert_error(reject_response, allowed_statuses={400, 409})


def test_close_same_order_twice_should_fail_second_time():
    order = create_order(sample_id="DOUBLE-CLOSE-001")
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    approve_payload = approve_with_optional_quota_override(order_id)
    assert approve_payload["data"]["status"] == "approved"

    assert_success(action(order_id, "confirm_delivery", actor_id="user001"), 200)
    assert_success(action(order_id, "confirm_received", actor_id="labstaff001"), 200)
    assert_success(action(order_id, "ready_for_pickup", actor_id="labstaff001"), 200)

    close_payload = assert_success(action(order_id, "close", actor_id="labstaff001"), 200)
    assert close_payload["data"]["status"] == "closed"

    second_close = action(order_id, "close", actor_id="labstaff001")
    assert_error(second_close, allowed_statuses={400, 409})


def test_cancel_after_approved_should_fail():
    order = create_order(sample_id="CANCEL-AFTER-APPROVE-001")
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    approve_payload = approve_with_optional_quota_override(order_id)
    assert approve_payload["data"]["status"] == "approved"

    cancel_response = action(order_id, "cancel", actor_id="user001")

    assert_error(cancel_response, allowed_statuses={400, 409})


# ============================================================
# Role Permission Tests
# 如果目前後端尚未實作角色權限，這幾個會 fail。
# fail 代表規格尚未真正被後端保護。
# ============================================================


def test_factory_user_cannot_approve_order():
    order = create_order(sample_id="ROLE-FACTORY-APPROVE-001")
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    response = action(
        order_id,
        "approve",
        actor_id="user001",
        reason="廠區使用者不應可核准",
        quota_override=True,
    )

    assert_error(response, allowed_statuses={400, 403, 409})


def test_lab_staff_cannot_reject_order():
    order = create_order(sample_id="ROLE-LABSTAFF-REJECT-001")
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    response = action(
        order_id,
        "reject",
        actor_id="labstaff001",
        reason="實驗室人員不應可拒絕",
    )

    assert_error(response, allowed_statuses={400, 403, 409})


def test_manager_can_approve_order():
    order = create_order(sample_id="ROLE-MANAGER-APPROVE-001")
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    payload = approve_with_optional_quota_override(order_id)

    assert payload["data"]["status"] == "approved"


def test_factory_user_cannot_confirm_received():
    order = create_order(sample_id="ROLE-FACTORY-RECEIVED-001")
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    approve_payload = approve_with_optional_quota_override(order_id)
    assert approve_payload["data"]["status"] == "approved"

    assert_success(action(order_id, "confirm_delivery", actor_id="user001"), 200)

    response = action(order_id, "confirm_received", actor_id="user001")

    assert_error(response, allowed_statuses={400, 403, 409})


def test_lab_staff_can_confirm_received():
    order = create_order(sample_id="ROLE-LABSTAFF-RECEIVED-001")
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    approve_payload = approve_with_optional_quota_override(order_id)
    assert approve_payload["data"]["status"] == "approved"

    assert_success(action(order_id, "confirm_delivery", actor_id="user001"), 200)

    payload = assert_success(action(order_id, "confirm_received", actor_id="labstaff001"), 200)

    assert payload["data"]["status"] == "sample_received"


# ============================================================
# Pagination / Filter Boundary Tests
# ============================================================


def test_get_order_list_with_unknown_status_returns_error_or_empty_list():
    response = client.get("/api/orders", params={"status": "not_a_status"})

    if response.status_code == 200:
        payload = response.json()
        assert isinstance(payload["data"], list)
    else:
        assert_error(response, allowed_statuses={400, 422})


def test_get_order_list_with_invalid_page_or_limit_returns_error_or_safe_result():
    invalid_queries = [
        {"page": 0, "limit": 10},
        {"page": -1, "limit": 10},
        {"page": 1, "limit": 0},
        {"page": 1, "limit": -5},
    ]

    for params in invalid_queries:
        response = client.get("/api/orders", params=params)

        if response.status_code == 200:
            payload = response.json()
            assert isinstance(payload["data"], list)
        else:
            assert_error(response, allowed_statuses={400, 422})


def test_get_order_list_filter_by_non_existing_applicant_returns_empty_or_error():
    response = client.get("/api/orders", params={"applicantId": "not_existing_user"})

    if response.status_code == 200:
        payload = response.json()
        assert isinstance(payload["data"], list)
        assert len(payload["data"]) == 0
    else:
        assert_error(response, allowed_statuses={400, 404, 422})


# ============================================================
# Additional Order Management Coverage
# Multi-items / master-data validation / history / guards
# ============================================================


def create_order_with_items(items, applicant_id="user001", department_id="D001", priority="normal"):
    response = client.post(
        "/api/orders",
        json={
            "applicantId": applicant_id,
            "departmentId": department_id,
            "priority": priority,
            "items": items,
        },
    )

    payload = assert_success(response, 201)
    order_id = payload["data"]["id"]

    detail_payload = assert_success(client.get(f"/api/orders/{order_id}"), 200)
    return detail_payload["data"]


# ============================================================
# 1. Multi-item Tests
# ============================================================


def test_create_order_with_multiple_items():
    order = create_order_with_items(
        [
            {
                "sampleId": "MULTI-001",
                "labId": "LAB001",
                "experimentId": "EXP001",
            },
            {
                "sampleId": "MULTI-002",
                "labId": "LAB001",
                "experimentId": "EXP002",
            },
            {
                "sampleId": "MULTI-003",
                "labId": "LAB002",
                "experimentId": "EXP003",
            },
        ]
    )

    assert order["status"] == "draft"
    assert order["totalItems"] == 3
    assert len(order["items"]) == 3

    sample_ids = {item["sampleId"] for item in order["items"]}
    assert "MULTI-001" in sample_ids
    assert "MULTI-002" in sample_ids
    assert "MULTI-003" in sample_ids


def test_create_order_allows_multiple_items_to_share_sample():
    order = create_order_with_items(
        [
            {
                "sampleId": "SHARED-SAMPLE-001",
                "labId": "LAB001",
                "experimentId": "EXP001",
            },
            {
                "sampleId": "SHARED-SAMPLE-001",
                "labId": "LAB001",
                "experimentId": "EXP002",
            },
            {
                "sampleId": "SHARED-SAMPLE-001",
                "labId": "LAB002",
                "experimentId": "EXP003",
            },
        ]
    )

    assert order["status"] == "draft"
    assert order["totalItems"] == 3
    assert [
        (item["sampleId"], item["labId"], item["experimentId"])
        for item in order["items"]
    ] == [
        ("SHARED-SAMPLE-001", "LAB001", "EXP001"),
        ("SHARED-SAMPLE-001", "LAB001", "EXP002"),
        ("SHARED-SAMPLE-001", "LAB002", "EXP003"),
    ]


def test_patch_order_can_increase_item_count():
    order = create_order(sample_id="PATCH-INCREASE-001")
    order_id = order["id"]

    response = client.patch(
        f"/api/orders/{order_id}",
        json={
            "departmentId": "D001",
            "priority": "normal",
            "items": [
                {
                    "sampleId": "PATCH-INCREASE-001",
                    "labId": "LAB001",
                    "experimentId": "EXP001",
                },
                {
                    "sampleId": "PATCH-INCREASE-002",
                    "labId": "LAB001",
                    "experimentId": "EXP002",
                },
            ],
        },
    )

    payload = assert_success(response, 200)
    data = payload["data"]

    assert data["totalItems"] == 2
    assert len(data["items"]) == 2


def test_patch_order_can_decrease_item_count():
    order = create_order_with_items(
        [
            {
                "sampleId": "PATCH-DECREASE-001",
                "labId": "LAB001",
                "experimentId": "EXP001",
            },
            {
                "sampleId": "PATCH-DECREASE-002",
                "labId": "LAB001",
                "experimentId": "EXP002",
            },
        ]
    )
    order_id = order["id"]

    response = client.patch(
        f"/api/orders/{order_id}",
        json={
            "departmentId": "D001",
            "priority": "normal",
            "items": [
                {
                    "sampleId": "PATCH-DECREASE-001",
                    "labId": "LAB001",
                    "experimentId": "EXP001",
                }
            ],
        },
    )

    payload = assert_success(response, 200)
    data = payload["data"]

    assert data["totalItems"] == 1
    assert len(data["items"]) == 1


def test_create_order_rejects_incomplete_item_inside_multiple_items():
    response = client.post(
        "/api/orders",
        json={
            "applicantId": "user001",
            "departmentId": "D001",
            "priority": "normal",
            "items": [
                {
                    "sampleId": "VALID-001",
                    "labId": "LAB001",
                    "experimentId": "EXP001",
                },
                {
                    "sampleId": "INVALID-002",
                    "labId": "",
                    "experimentId": "EXP002",
                },
            ],
        },
    )

    assert_error(response, allowed_statuses={400, 422})


# ============================================================
# 2. Master Data Validation Tests
# ============================================================


def test_create_order_rejects_unknown_department():
    response = client.post(
        "/api/orders",
        json={
            "applicantId": "user001",
            "departmentId": "UNKNOWN_DEPT",
            "priority": "normal",
            "items": [
                {
                    "sampleId": "UNKNOWN-DEPT-001",
                    "labId": "LAB001",
                    "experimentId": "EXP001",
                }
            ],
        },
    )

    assert_error(response, allowed_statuses={400, 404, 422})


def test_create_order_rejects_unknown_lab():
    response = client.post(
        "/api/orders",
        json={
            "applicantId": "user001",
            "departmentId": "D001",
            "priority": "normal",
            "items": [
                {
                    "sampleId": "UNKNOWN-LAB-001",
                    "labId": "UNKNOWN_LAB",
                    "experimentId": "EXP001",
                }
            ],
        },
    )

    assert_error(response, allowed_statuses={400, 404, 422})


def test_create_order_rejects_unknown_experiment():
    response = client.post(
        "/api/orders",
        json={
            "applicantId": "user001",
            "departmentId": "D001",
            "priority": "normal",
            "items": [
                {
                    "sampleId": "UNKNOWN-EXP-001",
                    "labId": "LAB001",
                    "experimentId": "UNKNOWN_EXP",
                }
            ],
        },
    )

    assert_error(response, allowed_statuses={400, 404, 422})


def test_create_order_rejects_lab_experiment_mismatch():
    response = client.post(
        "/api/orders",
        json={
            "applicantId": "user001",
            "departmentId": "D001",
            "priority": "normal",
            "items": [
                {
                    "sampleId": "LAB-EXP-MISMATCH-001",
                    "labId": "LAB002",
                    "experimentId": "EXP001",
                }
            ],
        },
    )

    assert_error(response, allowed_statuses={400, 404, 422})


def test_create_order_rejects_unknown_applicant_from_master_data_section():
    response = client.post(
        "/api/orders",
        json={
            "applicantId": "unknown_user",
            "departmentId": "D001",
            "priority": "normal",
            "items": [
                {
                    "sampleId": "UNKNOWN-USER-001",
                    "labId": "LAB001",
                    "experimentId": "EXP001",
                }
            ],
        },
    )

    assert_error(response, allowed_statuses={400, 404, 422})


# ============================================================
# 3. History Completeness Tests
# ============================================================


def test_history_records_full_lifecycle_actions():
    order = create_order(sample_id="HISTORY-FULL-001")
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    approve_response = action(order_id, "approve", actor_id="manager001")

    if approve_response.status_code >= 400:
        assert_success(
            action(
                order_id,
                "approve",
                actor_id="manager001",
                reason="測試環境配額不足，使用特批核准",
                quota_override=True,
            ),
            200,
        )
    else:
        assert_success(approve_response, 200)

    assert_success(action(order_id, "confirm_delivery", actor_id="user001"), 200)
    assert_success(action(order_id, "confirm_received", actor_id="labstaff001"), 200)
    assert_success(action(order_id, "ready_for_pickup", actor_id="labstaff001"), 200)
    assert_success(action(order_id, "close", actor_id="labstaff001"), 200)

    history_payload = assert_success(client.get(f"/api/orders/{order_id}/history"), 200)
    actions = [item["action"] for item in history_payload["data"]]

    assert "create" in actions
    assert "submit" in actions
    assert "approve" in actions
    assert "confirm_delivery" in actions
    assert "confirm_received" in actions
    assert "ready_for_pickup" in actions
    assert "close" in actions


def test_history_records_submit_return_resubmit_sequence():
    order = create_order(sample_id="HISTORY-RETURN-RESUBMIT-001")
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    reason = "補件後重新送出測試"
    assert_success(
        action(order_id, "return", actor_id="manager001", reason=reason),
        200,
    )

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    history_payload = assert_success(client.get(f"/api/orders/{order_id}/history"), 200)
    history = history_payload["data"]

    submit_count = sum(1 for item in history if item["action"] == "submit")
    return_records = [item for item in history if item["action"] == "return" and item.get("reason") == reason]

    assert submit_count >= 2
    assert len(return_records) == 1


def test_approve_failure_should_not_write_approve_history():
    order = create_order(sample_id="HISTORY-APPROVE-FAIL-001")
    order_id = order["id"]

    response = action(order_id, "approve", actor_id="manager001")
    assert_error(response, allowed_statuses={400, 409})

    history_payload = assert_success(client.get(f"/api/orders/{order_id}/history"), 200)
    actions = [item["action"] for item in history_payload["data"]]

    assert "approve" not in actions


# ============================================================
# 4. State Transition Guard Matrix
# ============================================================


def test_draft_should_not_allow_approval_stage_actions():
    order = create_order(sample_id="GUARD-DRAFT-001")
    order_id = order["id"]

    invalid_actions = [
        ("approve", "manager001", "draft should not approve"),
        ("return", "manager001", "draft should not return"),
        ("reject", "manager001", "draft should not reject"),
        ("confirm_delivery", "user001", None),
        ("confirm_received", "labstaff001", None),
        ("ready_for_pickup", "labstaff001", None),
        ("close", "labstaff001", None),
    ]

    for action_name, actor_id, reason in invalid_actions:
        response = action(order_id, action_name, actor_id=actor_id, reason=reason)
        assert_error(response, allowed_statuses={400, 409})


def test_pending_approval_should_not_allow_delivery_or_close_actions():
    order = create_order(sample_id="GUARD-PENDING-001")
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    invalid_actions = [
        ("confirm_delivery", "user001"),
        ("confirm_received", "labstaff001"),
        ("ready_for_pickup", "labstaff001"),
        ("close", "labstaff001"),
    ]

    for action_name, actor_id in invalid_actions:
        response = action(order_id, action_name, actor_id=actor_id)
        assert_error(response, allowed_statuses={400, 409})


def test_approved_should_not_allow_submit_return_reject_or_delete():
    order = create_order(sample_id="GUARD-APPROVED-001")
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    approve_response = action(order_id, "approve", actor_id="manager001")

    if approve_response.status_code >= 400:
        assert_success(
            action(
                order_id,
                "approve",
                actor_id="manager001",
                reason="測試環境配額不足，使用特批核准",
                quota_override=True,
            ),
            200,
        )
    else:
        assert_success(approve_response, 200)

    invalid_actions = [
        ("submit", "user001", None),
        ("return", "manager001", "approved should not return"),
        ("reject", "manager001", "approved should not reject"),
    ]

    for action_name, actor_id, reason in invalid_actions:
        response = action(order_id, action_name, actor_id=actor_id, reason=reason)
        assert_error(response, allowed_statuses={400, 409})

    delete_response = client.delete(f"/api/orders/{order_id}")
    assert_error(delete_response, allowed_statuses={400, 409})


def test_terminal_statuses_should_not_allow_any_action():
    terminal_cases = []

    # cancelled
    cancelled_order = create_order(sample_id="TERMINAL-CANCELLED-001")
    assert_success(action(cancelled_order["id"], "cancel", actor_id="user001"), 200)
    terminal_cases.append(cancelled_order["id"])

    # rejected
    rejected_order = create_order(sample_id="TERMINAL-REJECTED-001")
    assert_success(action(rejected_order["id"], "submit", actor_id="user001"), 200)
    assert_success(
        action(
            rejected_order["id"],
            "reject",
            actor_id="manager001",
            reason="拒絕後不可再操作",
        ),
        200,
    )
    terminal_cases.append(rejected_order["id"])

    # closed
    closed_order = create_order(sample_id="TERMINAL-CLOSED-001")
    closed_order_id = closed_order["id"]
    assert_success(action(closed_order_id, "submit", actor_id="user001"), 200)

    approve_response = action(closed_order_id, "approve", actor_id="manager001")

    if approve_response.status_code >= 400:
        assert_success(
            action(
                closed_order_id,
                "approve",
                actor_id="manager001",
                reason="測試環境配額不足，使用特批核准",
                quota_override=True,
            ),
            200,
        )
    else:
        assert_success(approve_response, 200)

    assert_success(action(closed_order_id, "confirm_delivery", actor_id="user001"), 200)
    assert_success(action(closed_order_id, "confirm_received", actor_id="labstaff001"), 200)
    assert_success(action(closed_order_id, "ready_for_pickup", actor_id="labstaff001"), 200)
    assert_success(action(closed_order_id, "close", actor_id="labstaff001"), 200)
    terminal_cases.append(closed_order_id)

    invalid_actions = [
        ("submit", "user001", None),
        ("approve", "manager001", None),
        ("return", "manager001", "terminal should not return"),
        ("reject", "manager001", "terminal should not reject"),
        ("confirm_delivery", "user001", None),
        ("confirm_received", "labstaff001", None),
        ("ready_for_pickup", "labstaff001", None),
        ("close", "labstaff001", None),
        ("cancel", "user001", None),
    ]

    for order_id in terminal_cases:
        for action_name, actor_id, reason in invalid_actions:
            response = action(order_id, action_name, actor_id=actor_id, reason=reason)
            assert_error(response, allowed_statuses={400, 409})


# ============================================================
# 5. Soft Delete Consistency
# ============================================================


def test_soft_deleted_order_should_not_appear_in_list_or_applicant_list():
    order = create_order(sample_id="SOFT-DELETE-LIST-001")
    order_id = order["id"]

    assert_success(client.delete(f"/api/orders/{order_id}"), 200)

    list_payload = assert_success(client.get("/api/orders"), 200)
    assert all(item["id"] != order_id for item in list_payload["data"])

    applicant_payload = assert_success(client.get("/api/orders/applicant/user001"), 200)
    assert all(item["id"] != order_id for item in applicant_payload["data"])


def test_soft_deleted_order_cannot_be_updated_or_actioned():
    order = create_order(sample_id="SOFT-DELETE-ACTION-001")
    order_id = order["id"]

    assert_success(client.delete(f"/api/orders/{order_id}"), 200)

    update_response = client.patch(
        f"/api/orders/{order_id}",
        json={
            "departmentId": "D001",
            "priority": "normal",
            "items": [
                {
                    "sampleId": "SOFT-DELETE-ACTION-UPDATED",
                    "labId": "LAB001",
                    "experimentId": "EXP001",
                }
            ],
        },
    )
    assert_error(update_response, allowed_statuses={400, 404, 409})

    submit_response = action(order_id, "submit", actor_id="user001")
    assert_error(submit_response, allowed_statuses={400, 404, 409})


# ============================================================
# 6. Quota Response Shape
# 修正版：used / limit 在 checks[] 裡，不一定在最外層
# ============================================================


def test_quota_check_api_returns_required_fields_strict_shape():
    response = client.get(
        "/api/quotas/check",
        params={
            "applicantId": "user001",
            "departmentId": "D001",
            "itemCount": 1,
        },
    )

    payload = assert_success(response, 200)
    data = payload["data"]

    assert "allowed" in data
    assert "needOverride" in data
    assert "checks" in data
    assert isinstance(data["checks"], list)
    assert len(data["checks"]) > 0

    for check in data["checks"]:
        assert "allowed" in check
        assert "limit" in check

        assert "used" in check
        assert "requested" in check


# ============================================================
# Additional Coverage: Item-level Approval / Quota Usage
# ============================================================


def action_for_item(
    order_id,
    action_name,
    order_item_id,
    actor_id="manager001",
    reason=None,
    quota_override=False,
):
    body = {
        "action": action_name,
        "actorId": actor_id,
        "orderItemId": order_item_id,
    }

    if reason is not None:
        body["reason"] = reason

    if quota_override:
        body["quotaOverride"] = True

    return client.post(f"/api/orders/{order_id}/actions", json=body)


def approve_order_flexibly(order_id, actor_id="manager001", reason="測試環境配額不足，使用特批核准"):
    response = action(order_id, "approve", actor_id=actor_id)

    if response.status_code == 200:
        return assert_success(response, 200)

    return assert_success(
        action(
            order_id,
            "approve",
            actor_id=actor_id,
            reason=reason,
            quota_override=True,
        ),
        200,
    )


def approve_item_flexibly(
    order_id,
    order_item_id,
    actor_id="manager001",
    reason="測試環境配額不足，使用特批核准",
):
    response = action_for_item(
        order_id,
        "approve",
        order_item_id,
        actor_id=actor_id,
    )

    if response.status_code == 200:
        return assert_success(response, 200)

    return assert_success(
        action_for_item(
            order_id,
            "approve",
            order_item_id,
            actor_id=actor_id,
            reason=reason,
            quota_override=True,
        ),
        200,
    )


def get_order_detail(order_id):
    return assert_success(client.get(f"/api/orders/{order_id}"), 200)["data"]


def get_quota_used_count(scope_type, scope_id):
    payload = assert_success(client.get("/api/quotas"), 200)
    quotas = payload["data"]

    quota = next(item for item in quotas if item["scopeType"] == scope_type and item["scopeId"] == scope_id)

    return quota["usedCount"]


# ============================================================
# 1. 不同實驗室主管子單簽核
# ============================================================


def test_cross_lab_managers_approve_only_their_own_lab_items():
    order = create_order_with_items(
        [
            {
                "sampleId": "CROSS-LAB-001",
                "labId": "LAB001",
                "experimentId": "EXP001",
            },
            {
                "sampleId": "CROSS-LAB-002",
                "labId": "LAB003",
                "experimentId": "EXP004",
            },
        ]
    )
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    detail = get_order_detail(order_id)
    lab001_item = next(item for item in detail["items"] if item["labId"] == "LAB001")
    lab003_item = next(item for item in detail["items"] if item["labId"] == "LAB003")

    response = action_for_item(
        order_id,
        "approve",
        lab001_item["id"],
        actor_id="manager001",
    )
    assert_success(response, 200)

    detail = get_order_detail(order_id)
    lab001_item = next(item for item in detail["items"] if item["labId"] == "LAB001")
    lab003_item = next(item for item in detail["items"] if item["labId"] == "LAB003")

    assert detail["status"] == "pending_approval"
    assert lab001_item["status"] == "approved"
    assert lab001_item["approvedBy"] == "manager001"
    assert lab003_item["status"] == "pending_approval"

    response = action_for_item(
        order_id,
        "approve",
        lab003_item["id"],
        actor_id="manager003",
    )
    assert_success(response, 200)

    detail = get_order_detail(order_id)
    lab001_item = next(item for item in detail["items"] if item["labId"] == "LAB001")
    lab003_item = next(item for item in detail["items"] if item["labId"] == "LAB003")

    assert detail["status"] == "approved"
    assert lab001_item["status"] == "approved"
    assert lab003_item["status"] == "approved"
    assert lab003_item["approvedBy"] == "manager003"


def test_manager_cannot_approve_other_lab_item_by_order_item_id():
    order = create_order_with_items(
        [
            {
                "sampleId": "OTHER-LAB-001",
                "labId": "LAB003",
                "experimentId": "EXP004",
            }
        ]
    )
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    detail = get_order_detail(order_id)
    lab003_item = detail["items"][0]

    response = action_for_item(
        order_id,
        "approve",
        lab003_item["id"],
        actor_id="manager001",
        reason="manager001 不應可核准 LAB003",
        quota_override=True,
    )

    assert_error(response, allowed_statuses={400, 403, 409})

    detail = get_order_detail(order_id)
    assert detail["status"] == "pending_approval"
    assert detail["items"][0]["status"] == "pending_approval"


def test_manager_approving_without_order_item_id_only_affects_own_labs():
    order = create_order_with_items(
        [
            {
                "sampleId": "OWN-LAB-001",
                "labId": "LAB001",
                "experimentId": "EXP001",
            },
            {
                "sampleId": "OWN-LAB-002",
                "labId": "LAB003",
                "experimentId": "EXP004",
            },
        ]
    )
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    response = action(order_id, "approve", actor_id="manager001")
    assert_success(response, 200)

    detail = get_order_detail(order_id)
    lab001_item = next(item for item in detail["items"] if item["labId"] == "LAB001")
    lab003_item = next(item for item in detail["items"] if item["labId"] == "LAB003")

    assert detail["status"] == "pending_approval"
    assert lab001_item["status"] == "approved"
    assert lab003_item["status"] == "pending_approval"

    response = action(order_id, "approve", actor_id="manager003")
    assert_success(response, 200)

    detail = get_order_detail(order_id)
    assert detail["status"] == "approved"


def test_return_one_lab_item_keeps_main_order_returned_and_records_item_reason():
    order = create_order_with_items(
        [
            {
                "sampleId": "RETURN-ITEM-001",
                "labId": "LAB001",
                "experimentId": "EXP001",
            },
            {
                "sampleId": "RETURN-ITEM-002",
                "labId": "LAB003",
                "experimentId": "EXP004",
            },
        ]
    )
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    detail = get_order_detail(order_id)
    lab003_item = next(item for item in detail["items"] if item["labId"] == "LAB003")

    reason = "LAB003 項目需要補件"
    response = action_for_item(
        order_id,
        "return",
        lab003_item["id"],
        actor_id="manager003",
        reason=reason,
    )
    assert_success(response, 200)

    detail = get_order_detail(order_id)
    lab001_item = next(item for item in detail["items"] if item["labId"] == "LAB001")
    lab003_item = next(item for item in detail["items"] if item["labId"] == "LAB003")

    assert detail["status"] == "returned"
    assert lab001_item["status"] == "pending_approval"
    assert lab003_item["status"] == "returned"
    assert lab003_item["returnReason"] == reason

    response = action(order_id, "confirm_delivery", actor_id="user001")
    assert_error(response, allowed_statuses={400, 409})


def test_reject_one_lab_item_rejects_all_order_items():
    order = create_order_with_items(
        [
            {
                "sampleId": "REJECT-ALL-001",
                "labId": "LAB001",
                "experimentId": "EXP001",
            },
            {
                "sampleId": "REJECT-ALL-002",
                "labId": "LAB003",
                "experimentId": "EXP004",
            },
        ]
    )
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    detail = get_order_detail(order_id)
    lab003_item = next(item for item in detail["items"] if item["labId"] == "LAB003")

    reason = "LAB003 rejects this order"
    response = action_for_item(
        order_id,
        "reject",
        lab003_item["id"],
        actor_id="manager003",
        reason=reason,
    )
    assert_success(response, 200)

    detail = get_order_detail(order_id)
    assert detail["status"] == "rejected"
    assert all(item["status"] == "rejected" for item in detail["items"])
    assert all(item["rejectReason"] == reason for item in detail["items"])


# ============================================================
# 2. Quota usage 累加與不累加
# ============================================================


def test_quota_usage_increases_after_order_fully_approved():
    before_user_used = get_quota_used_count("user", "user001")
    before_department_used = get_quota_used_count("department", "D001")

    order = create_order_with_items(
        [
            {
                "sampleId": "QUOTA-USAGE-001",
                "labId": "LAB001",
                "experimentId": "EXP001",
            },
            {
                "sampleId": "QUOTA-USAGE-002",
                "labId": "LAB001",
                "experimentId": "EXP002",
            },
        ]
    )
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    payload = approve_order_flexibly(order_id, actor_id="manager001")
    assert payload["data"]["status"] == "approved"

    after_user_used = get_quota_used_count("user", "user001")
    after_department_used = get_quota_used_count("department", "D001")

    assert after_user_used == before_user_used + 2
    assert after_department_used == before_department_used + 2


def test_quota_usage_does_not_increase_when_order_is_returned():
    before_user_used = get_quota_used_count("user", "user001")
    before_department_used = get_quota_used_count("department", "D001")

    order = create_order(sample_id="QUOTA-RETURN-001")
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)
    assert_success(
        action(
            order_id,
            "return",
            actor_id="manager001",
            reason="退回不應增加 quota usage",
        ),
        200,
    )

    after_user_used = get_quota_used_count("user", "user001")
    after_department_used = get_quota_used_count("department", "D001")

    assert after_user_used == before_user_used
    assert after_department_used == before_department_used


def test_quota_usage_does_not_increase_when_order_is_rejected():
    before_user_used = get_quota_used_count("user", "user001")
    before_department_used = get_quota_used_count("department", "D001")

    order = create_order(sample_id="QUOTA-REJECT-001")
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)
    assert_success(
        action(
            order_id,
            "reject",
            actor_id="manager001",
            reason="拒絕不應增加 quota usage",
        ),
        200,
    )

    after_user_used = get_quota_used_count("user", "user001")
    after_department_used = get_quota_used_count("department", "D001")

    assert after_user_used == before_user_used
    assert after_department_used == before_department_used


def test_quota_usage_does_not_increase_before_approval():
    before_user_used = get_quota_used_count("user", "user001")
    before_department_used = get_quota_used_count("department", "D001")

    order = create_order(sample_id="QUOTA-PENDING-001")
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    after_submit_user_used = get_quota_used_count("user", "user001")
    after_submit_department_used = get_quota_used_count("department", "D001")

    assert after_submit_user_used == before_user_used
    assert after_submit_department_used == before_department_used

    payload = approve_order_flexibly(order_id, actor_id="manager001")
    assert payload["data"]["status"] == "approved"

    after_approve_user_used = get_quota_used_count("user", "user001")
    after_approve_department_used = get_quota_used_count("department", "D001")

    assert after_approve_user_used == before_user_used + 1
    assert after_approve_department_used == before_department_used + 1


def test_quota_usage_is_not_duplicated_by_second_approve_attempt():
    before_user_used = get_quota_used_count("user", "user001")
    before_department_used = get_quota_used_count("department", "D001")

    order = create_order(sample_id="QUOTA-NO-DUPLICATE-001")
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    payload = approve_order_flexibly(order_id, actor_id="manager001")
    assert payload["data"]["status"] == "approved"

    after_first_user_used = get_quota_used_count("user", "user001")
    after_first_department_used = get_quota_used_count("department", "D001")

    assert after_first_user_used == before_user_used + 1
    assert after_first_department_used == before_department_used + 1

    second_response = action(order_id, "approve", actor_id="manager001")
    assert_error(second_response, allowed_statuses={400, 409})

    after_second_user_used = get_quota_used_count("user", "user001")
    after_second_department_used = get_quota_used_count("department", "D001")

    assert after_second_user_used == after_first_user_used
    assert after_second_department_used == after_first_department_used


# ============================================================
# Additional Coverage: Priority Orders, orderItemId Guard,
# Returned Update Reset, OrderNo, API Shape
# ============================================================

import re


def consume_one_monthly_quota_item(sample_id: str):
    seed_order = create_order_with_items(
        [
            {
                "sampleId": sample_id,
                "labId": "LAB001",
                "experimentId": "EXP001",
            }
        ]
    )

    assert_success(action(seed_order["id"], "submit", actor_id="user001"), 200)
    assert_success(action(seed_order["id"], "approve", actor_id="manager001"), 200)


def test_urgent_order_monthly_quota_exceeded_requires_override_and_override_success():
    consume_one_monthly_quota_item("URGENT-QUOTA-SEED")

    items = [
        {
            "sampleId": f"URGENT-QUOTA-{index}",
            "labId": "LAB001",
            "experimentId": "EXP001" if index % 2 == 0 else "EXP002",
        }
        for index in range(10)
    ]

    order = create_order_with_items(items, priority="urgent")
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    normal_response = action(order_id, "approve", actor_id="manager001")
    assert_error(normal_response, allowed_statuses={400, 409})

    override_payload = assert_success(
        action(
            order_id,
            "approve",
            actor_id="manager001",
            reason="急件配額超額，主管特批",
            quota_override=True,
        ),
        200,
    )

    assert override_payload["data"]["status"] == "approved"

    detail = get_order_detail(order_id)
    assert detail["status"] == "approved"
    assert all(item["status"] == "approved" for item in detail["items"])


def test_critical_order_monthly_quota_exceeded_requires_override_and_override_success():
    consume_one_monthly_quota_item("CRITICAL-QUOTA-SEED")

    items = [
        {
            "sampleId": f"CRITICAL-QUOTA-{index}",
            "labId": "LAB001",
            "experimentId": "EXP001" if index % 2 == 0 else "EXP002",
        }
        for index in range(10)
    ]

    order = create_order_with_items(items, priority="critical")
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    normal_response = action(order_id, "approve", actor_id="manager001")
    assert_error(normal_response, allowed_statuses={400, 409})

    override_payload = assert_success(
        action(
            order_id,
            "approve",
            actor_id="manager001",
            reason="特急件配額超額，主管特批",
            quota_override=True,
        ),
        200,
    )

    assert override_payload["data"]["status"] == "approved"

    detail = get_order_detail(order_id)
    assert detail["status"] == "approved"
    assert all(item["status"] == "approved" for item in detail["items"])


def test_urgent_order_increases_monthly_quota_usage_after_approval():
    before = assert_success(
        client.get(
            "/api/quotas/check",
            params={
                "applicantId": "user001",
                "departmentId": "D001",
                "itemCount": 1,
                "priority": "urgent",
            },
        ),
        200,
    )["data"]

    before_user_check = next(item for item in before["checks"] if item["scopeType"] == "user" and item["scopeId"] == "user001")
    before_department_check = next(item for item in before["checks"] if item["scopeType"] == "department" and item["scopeId"] == "D001")

    order = create_order_with_items(
        [
            {
                "sampleId": "URGENT-USAGE-001",
                "labId": "LAB001",
                "experimentId": "EXP001",
            },
            {
                "sampleId": "URGENT-USAGE-002",
                "labId": "LAB001",
                "experimentId": "EXP002",
            },
        ],
        priority="urgent",
    )
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    payload = approve_order_flexibly(order_id, actor_id="manager001")
    assert payload["data"]["status"] == "approved"

    after = assert_success(
        client.get(
            "/api/quotas/check",
            params={
                "applicantId": "user001",
                "departmentId": "D001",
                "itemCount": 1,
                "priority": "urgent",
            },
        ),
        200,
    )["data"]

    after_user_check = next(item for item in after["checks"] if item["scopeType"] == "user" and item["scopeId"] == "user001")
    after_department_check = next(item for item in after["checks"] if item["scopeType"] == "department" and item["scopeId"] == "D001")

    assert after_user_check["used"] == before_user_check["used"] + 2
    assert after_department_check["used"] == before_department_check["used"] + 2


def test_critical_order_increases_monthly_quota_usage_after_approval():
    before = assert_success(
        client.get(
            "/api/quotas/check",
            params={
                "applicantId": "user001",
                "departmentId": "D001",
                "itemCount": 1,
                "priority": "critical",
            },
        ),
        200,
    )["data"]

    before_user_check = next(item for item in before["checks"] if item["scopeType"] == "user" and item["scopeId"] == "user001")
    before_department_check = next(item for item in before["checks"] if item["scopeType"] == "department" and item["scopeId"] == "D001")

    order = create_order_with_items(
        [
            {
                "sampleId": "CRITICAL-USAGE-001",
                "labId": "LAB001",
                "experimentId": "EXP001",
            },
        ],
        priority="critical",
    )
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    payload = approve_order_flexibly(order_id, actor_id="manager001")
    assert payload["data"]["status"] == "approved"

    after = assert_success(
        client.get(
            "/api/quotas/check",
            params={
                "applicantId": "user001",
                "departmentId": "D001",
                "itemCount": 1,
                "priority": "critical",
            },
        ),
        200,
    )["data"]

    after_user_check = next(item for item in after["checks"] if item["scopeType"] == "user" and item["scopeId"] == "user001")
    after_department_check = next(item for item in after["checks"] if item["scopeType"] == "department" and item["scopeId"] == "D001")

    assert after_user_check["used"] == before_user_check["used"] + 1
    assert after_department_check["used"] == before_department_check["used"] + 1


# ============================================================
# orderItemId Boundary Tests
# ============================================================


def test_approve_with_non_existing_order_item_id_should_fail():
    order = create_order(sample_id="BAD-ITEM-ID-001")
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    response = action_for_item(
        order_id,
        "approve",
        999999999,
        actor_id="manager001",
        reason="不存在的明細不應可核准",
        quota_override=True,
    )

    assert_error(response, allowed_statuses={400, 403, 404, 409})

    detail = get_order_detail(order_id)
    assert detail["status"] == "pending_approval"
    assert detail["items"][0]["status"] == "pending_approval"


def test_approve_with_order_item_id_from_another_order_should_fail():
    order_a = create_order(sample_id="CROSS-ORDER-A-001")
    order_b = create_order(sample_id="CROSS-ORDER-B-001")

    order_a_id = order_a["id"]
    order_b_id = order_b["id"]

    assert_success(action(order_a_id, "submit", actor_id="user001"), 200)
    assert_success(action(order_b_id, "submit", actor_id="user001"), 200)

    order_b_detail = get_order_detail(order_b_id)
    foreign_item_id = order_b_detail["items"][0]["id"]

    response = action_for_item(
        order_a_id,
        "approve",
        foreign_item_id,
        actor_id="manager001",
        reason="不可用其他委託單的 orderItemId",
        quota_override=True,
    )

    assert_error(response, allowed_statuses={400, 403, 404, 409})

    order_a_detail = get_order_detail(order_a_id)
    assert order_a_detail["status"] == "pending_approval"
    assert order_a_detail["items"][0]["status"] == "pending_approval"


def test_approved_item_cannot_be_returned_again():
    order = create_order_with_items(
        [
            {
                "sampleId": "APPROVED-ITEM-001",
                "labId": "LAB001",
                "experimentId": "EXP001",
            },
            {
                "sampleId": "APPROVED-ITEM-002",
                "labId": "LAB003",
                "experimentId": "EXP004",
            },
        ]
    )
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    detail = get_order_detail(order_id)
    lab001_item = next(item for item in detail["items"] if item["labId"] == "LAB001")

    approve_payload = approve_item_flexibly(
        order_id,
        lab001_item["id"],
        actor_id="manager001",
    )
    assert approve_payload["data"]["status"] == "pending_approval"

    response = action_for_item(
        order_id,
        "return",
        lab001_item["id"],
        actor_id="manager001",
        reason="已核准 item 不應可再退回",
    )

    assert_error(response, allowed_statuses={400, 403, 409})

    detail = get_order_detail(order_id)
    lab001_item = next(item for item in detail["items"] if item["labId"] == "LAB001")
    assert lab001_item["status"] == "approved"


def test_returned_item_cannot_be_approved_by_wrong_manager():
    order = create_order_with_items(
        [
            {
                "sampleId": "RETURN-WRONG-MANAGER-001",
                "labId": "LAB003",
                "experimentId": "EXP004",
            }
        ]
    )
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    detail = get_order_detail(order_id)
    lab003_item = detail["items"][0]

    assert_success(
        action_for_item(
            order_id,
            "return",
            lab003_item["id"],
            actor_id="manager003",
            reason="LAB003 補件",
        ),
        200,
    )

    response = action_for_item(
        order_id,
        "approve",
        lab003_item["id"],
        actor_id="manager001",
        reason="manager001 不應可核准 LAB003 returned item",
        quota_override=True,
    )

    assert_error(response, allowed_statuses={400, 403, 409})


# ============================================================
# Returned Update Reset Tests
# ============================================================


def test_update_returned_order_resets_item_status_and_reason():
    order = create_order(sample_id="RETURN-RESET-001")
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    reason = "原本的退回原因"
    assert_success(
        action(
            order_id,
            "return",
            actor_id="manager001",
            reason=reason,
        ),
        200,
    )

    returned_detail = get_order_detail(order_id)
    assert returned_detail["status"] == "returned"
    assert returned_detail["items"][0]["status"] == "returned"
    assert returned_detail["items"][0]["returnReason"] == reason

    update_payload = assert_success(
        client.patch(
            f"/api/orders/{order_id}",
            json={
                "departmentId": "D001",
                "priority": "normal",
                "items": [
                    {
                        "sampleId": "RETURN-RESET-UPDATED-001",
                        "labId": "LAB001",
                        "experimentId": "EXP002",
                    }
                ],
            },
        ),
        200,
    )

    updated_order = update_payload["data"]
    updated_item = updated_order["items"][0]

    assert updated_order["status"] == "returned"
    assert updated_item["status"] == "draft"
    assert updated_item["returnReason"] is None
    assert updated_item["rejectReason"] is None
    assert updated_item["approvedBy"] is None
    assert updated_item["approvedAt"] is None

    submit_payload = assert_success(action(order_id, "submit", actor_id="user001"), 200)
    assert submit_payload["data"]["status"] == "pending_approval"

    submitted_detail = get_order_detail(order_id)
    submitted_item = submitted_detail["items"][0]

    assert submitted_item["status"] == "pending_approval"
    assert submitted_item["returnReason"] is None
    assert submitted_item["rejectReason"] is None
    assert submitted_item["approvedBy"] is None


def test_update_returned_order_can_change_lab_and_experiment_then_resubmit():
    order = create_order(sample_id="RETURN-CHANGE-LAB-001")
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)
    assert_success(
        action(
            order_id,
            "return",
            actor_id="manager001",
            reason="改送其他實驗室",
        ),
        200,
    )

    update_payload = assert_success(
        client.patch(
            f"/api/orders/{order_id}",
            json={
                "departmentId": "D001",
                "priority": "normal",
                "items": [
                    {
                        "sampleId": "RETURN-CHANGE-LAB-UPDATED",
                        "labId": "LAB003",
                        "experimentId": "EXP004",
                    }
                ],
            },
        ),
        200,
    )

    item = update_payload["data"]["items"][0]
    assert item["labId"] == "LAB003"
    assert item["experimentId"] == "EXP004"
    assert item["status"] == "draft"

    assert_success(action(order_id, "submit", actor_id="user001"), 200)

    detail = get_order_detail(order_id)
    assert detail["status"] == "pending_approval"
    assert detail["items"][0]["labId"] == "LAB003"
    assert detail["items"][0]["status"] == "pending_approval"

    payload = approve_order_flexibly(order_id, actor_id="manager003")
    assert payload["data"]["status"] == "approved"


def test_update_returned_order_rejects_invalid_new_lab_experiment_mapping():
    order = create_order(sample_id="RETURN-INVALID-MAPPING-001")
    order_id = order["id"]

    assert_success(action(order_id, "submit", actor_id="user001"), 200)
    assert_success(
        action(
            order_id,
            "return",
            actor_id="manager001",
            reason="測試錯誤 mapping",
        ),
        200,
    )

    response = client.patch(
        f"/api/orders/{order_id}",
        json={
            "departmentId": "D001",
            "priority": "normal",
            "items": [
                {
                    "sampleId": "RETURN-INVALID-MAPPING-UPDATED",
                    "labId": "LAB003",
                    "experimentId": "EXP001",
                }
            ],
        },
    )

    assert_error(response, allowed_statuses={400, 422})


# ============================================================
# Order Number / API Response Shape Tests
# ============================================================


def test_order_number_is_unique_and_matches_expected_format():
    orders = [create_order(sample_id=f"ORDERNO-{index}") for index in range(5)]

    order_numbers = [order["orderNo"] for order in orders]

    assert len(order_numbers) == len(set(order_numbers))

    pattern = re.compile(r"^ORD-\d{8}-\d{3}-[A-F0-9]{4}$")

    for order_no in order_numbers:
        assert pattern.match(order_no), order_no


def test_success_responses_have_consistent_shape():
    order = create_order(sample_id="API-SHAPE-001")
    order_id = order["id"]

    responses = [
        client.get("/api/master-data"),
        client.get("/api/orders"),
        client.get(f"/api/orders/{order_id}"),
        client.get(f"/api/orders/{order_id}/history"),
        client.get("/api/quotas"),
        client.get("/api/samples"),
        client.get("/api/wips"),
        client.get("/api/reports"),
        client.get("/api/issues"),
    ]

    for response in responses:
        assert response.status_code == 200, response.text
        payload = response.json()
        assert "success" in payload
        assert payload["success"] is True
        assert "data" in payload


def test_order_list_response_has_pagination_shape():
    create_order(sample_id="PAGINATION-SHAPE-001")

    response = client.get(
        "/api/orders",
        params={
            "page": 1,
            "limit": 1,
        },
    )

    payload = assert_success(response, 200)

    assert "pagination" in payload
    assert "total" in payload["pagination"]
    assert "page" in payload["pagination"]
    assert "limit" in payload["pagination"]
    assert "totalPages" in payload["pagination"]

    assert payload["pagination"]["page"] == 1
    assert payload["pagination"]["limit"] == 1
    assert len(payload["data"]) <= 1


def test_error_response_has_detail_field():
    response = client.get("/api/orders/999999999")

    assert response.status_code == 404

    payload = response.json()
    assert "detail" in payload
    assert payload["detail"]


# ============================================================
# Final Extra Coverage: Quota API Validation / Admin Quota API
# ============================================================


def test_quota_check_rejects_zero_item_count():
    response = client.get(
        "/api/quotas/check",
        params={
            "applicantId": "user001",
            "departmentId": "D001",
            "itemCount": 0,
        },
    )

    assert_error(response, allowed_statuses={422})


def test_quota_check_rejects_negative_item_count():
    response = client.get(
        "/api/quotas/check",
        params={
            "applicantId": "user001",
            "departmentId": "D001",
            "itemCount": -1,
        },
    )

    assert_error(response, allowed_statuses={422})


def test_admin_can_create_quota_setting():
    response = client.post(
        "/api/quotas",
        json={
            "scopeType": "user",
            "scopeId": "quota_test_user",
            "monthlyLimit": 5,
            "isActive": True,
            "actorId": "admin001",
        },
    )

    payload = assert_success(response, 201)
    data = payload["data"]

    assert data["scopeType"] == "user"
    assert data["scopeId"] == "quota_test_user"
    assert data["monthlyLimit"] == 5
    assert data["isActive"] is True


def test_non_admin_cannot_create_quota_setting():
    response = client.post(
        "/api/quotas",
        json={
            "scopeType": "user",
            "scopeId": "quota_non_admin_user",
            "monthlyLimit": 5,
            "isActive": True,
            "actorId": "user001",
        },
    )

    assert_error(response, allowed_statuses={403})


def test_admin_can_update_quota_setting():
    create_response = client.post(
        "/api/quotas",
        json={
            "scopeType": "department",
            "scopeId": "D002",
            "monthlyLimit": 20,
            "isActive": True,
            "actorId": "admin001",
        },
    )

    create_payload = assert_success(create_response, 201)
    quota_id = create_payload["data"]["id"]

    update_response = client.patch(
        f"/api/quotas/{quota_id}",
        json={
            "monthlyLimit": 30,
            "isActive": False,
            "actorId": "admin001",
        },
    )

    update_payload = assert_success(update_response, 200)
    data = update_payload["data"]

    assert data["id"] == quota_id
    assert data["monthlyLimit"] == 30
    assert data["isActive"] is False


def test_non_admin_cannot_update_quota_setting():
    create_response = client.post(
        "/api/quotas",
        json={
            "scopeType": "department",
            "scopeId": "D003",
            "monthlyLimit": 20,
            "isActive": True,
            "actorId": "admin001",
        },
    )

    create_payload = assert_success(create_response, 201)
    quota_id = create_payload["data"]["id"]

    update_response = client.patch(
        f"/api/quotas/{quota_id}",
        json={
            "monthlyLimit": 99,
            "actorId": "manager001",
        },
    )

    assert_error(update_response, allowed_statuses={403})


def test_update_non_existing_quota_returns_404():
    response = client.patch(
        "/api/quotas/999999999",
        json={
            "monthlyLimit": 30,
            "actorId": "admin001",
        },
    )

    assert_error(response, allowed_statuses={404})


def test_create_quota_rejects_negative_limits():
    response = client.post(
        "/api/quotas",
        json={
            "scopeType": "user",
            "scopeId": "quota_invalid_limit",
            "monthlyLimit": -1,
            "isActive": True,
            "actorId": "admin001",
        },
    )

    assert_error(response, allowed_statuses={422})


def test_update_quota_rejects_negative_limits():
    create_response = client.post(
        "/api/quotas",
        json={
            "scopeType": "user",
            "scopeId": "quota_update_invalid_limit",
            "monthlyLimit": 10,
            "isActive": True,
            "actorId": "admin001",
        },
    )

    create_payload = assert_success(create_response, 201)
    quota_id = create_payload["data"]["id"]

    update_response = client.patch(
        f"/api/quotas/{quota_id}",
        json={
            "monthlyLimit": -10,
            "actorId": "admin001",
        },
    )

    assert_error(update_response, allowed_statuses={422})

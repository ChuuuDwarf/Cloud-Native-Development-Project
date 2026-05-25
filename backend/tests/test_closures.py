"""結單與倉儲 API 測試（對應 test_module_D.md T-011, T-012）。"""

STAFF = {"X-Role": "staff"}
CHIEF = {"X-Role": "chief"}


def test_list_closures(client):
    r = client.get("/api/closures")
    assert r.status_code == 200
    assert r.json()["total"] == 6


def test_check_closure_ready(client):
    r = client.get("/api/closures/WO-2024-0896/check")
    assert r.status_code == 200
    assert r.json()["data"]["canClose"] is True


def test_to_pickup_blocked_when_conditions_unmet(client):
    # WO-2024-0894 待結果確認，條件未滿足
    r = client.post("/api/closures/WO-2024-0894/to-pickup", headers=STAFF)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "INVALID_STATE"


def test_to_pickup_forbidden_for_user(client):
    # 廠區使用者無結單操作權限（主管則含人員權限，不在此測）
    r = client.post("/api/closures/WO-2024-0896/to-pickup", headers={"X-Role": "user"})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN"


def test_list_storage(client):
    r = client.get("/api/closures/storage")
    assert r.status_code == 200
    assert r.json()["total"] == 3


def test_outbound_then_close(client):
    # WO-2024-0896 為待取件，出庫取件後可結案
    r = client.post("/api/closures/WO-2024-0896/outbound", json={"operator": "倉管"}, headers=STAFF)
    assert r.status_code == 200
    assert all(s["status"] == "已取件" for s in r.json()["data"]["items"])
    r = client.post("/api/closures/WO-2024-0896/close", json={"operator": "倉管"}, headers=STAFF)
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "已結案"


def test_close_blocked_when_not_pending_pickup(client):
    # WO-2024-0894 非待取件，不可結案
    r = client.post("/api/closures/WO-2024-0894/close", json={"operator": "倉管"}, headers=STAFF)
    assert r.status_code == 409


def test_closure_order_not_found(client):
    r = client.get("/api/closures/WO-XXXX/check")
    assert r.status_code == 404

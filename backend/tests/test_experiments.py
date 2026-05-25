"""實驗執行 API 測試（對應 test_module_D.md T-001~T-009, T-013, T-015）。"""

STAFF = {"X-Role": "staff"}
CHIEF = {"X-Role": "chief"}


def test_list_experiments(client):
    r = client.get("/api/experiments")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 7
    assert len(body["data"]) == 7


def test_get_experiment_detail_with_history(client):
    r = client.get("/api/experiments/WIP-0891-01")
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["status"] == "執行中"
    assert any(h["action"] == "上機" for h in data["history"])


def test_checkin_success(client):
    r = client.post(
        "/api/experiments/WIP-0892-01/check-in",
        json={"operator": "李工", "machineId": "OPT-001", "recipe": "RCP-OPT-v2.0"},
        headers=STAFF,
    )
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "執行中"


def test_checkin_missing_field_returns_422(client):
    r = client.post("/api/experiments/WIP-0892-01/check-in", json={"operator": "x"}, headers=STAFF)
    assert r.status_code == 422


def test_checkin_allowed_for_chief(client):
    # 主管含實驗室人員權限，可執行上機
    r = client.post(
        "/api/experiments/WIP-0892-01/check-in",
        json={"operator": "主管", "machineId": "OPT-001", "recipe": "RCP-OPT-v2.0"},
        headers=CHIEF,
    )
    assert r.status_code == 200


def test_checkin_forbidden_for_user(client):
    # 廠區使用者無實驗操作權限
    r = client.post(
        "/api/experiments/WIP-0892-01/check-in",
        json={"operator": "x", "machineId": "O", "recipe": "r"},
        headers={"X-Role": "user"},
    )
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN"


def test_result_then_confirm_completes(client):
    client.post(
        "/api/experiments/WIP-0892-01/check-in",
        json={"operator": "李工", "machineId": "OPT-001", "recipe": "r"},
        headers=STAFF,
    )
    r = client.post(
        "/api/experiments/WIP-0892-01/result",
        json={"note": "量測完成", "dataVerified": True},
        headers=STAFF,
    )
    assert r.json()["data"]["status"] == "待確認"
    r = client.post(
        "/api/experiments/WIP-0892-01/confirm", json={"operator": "李工"}, headers=STAFF
    )
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "已完成"


def test_confirm_requires_verified_data(client):
    client.post(
        "/api/experiments/WIP-0892-01/check-in",
        json={"operator": "李工", "machineId": "OPT-001", "recipe": "r"},
        headers=STAFF,
    )
    client.post(
        "/api/experiments/WIP-0892-01/result",
        json={"note": "未驗證", "dataVerified": False},
        headers=STAFF,
    )
    r = client.post(
        "/api/experiments/WIP-0892-01/confirm", json={"operator": "李工"}, headers=STAFF
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_confirm_wrong_state_returns_409(client):
    # WIP-0891-01 為執行中，不可直接確認
    r = client.post("/api/experiments/WIP-0891-01/confirm", json={"operator": "x"}, headers=STAFF)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "INVALID_STATE"


def test_abort_request_then_chief_terminates(client):
    r = client.post(
        "/api/experiments/WIP-0891-01/abort-request", json={"reason": "設備異常"}, headers=STAFF
    )
    assert r.status_code == 200
    # 實驗室人員不可審核中止
    forbidden = client.post(
        "/api/experiments/WIP-0891-01/abort-review", json={"approve": True}, headers=STAFF
    )
    assert forbidden.status_code == 403
    # 主管核准終止
    r = client.post(
        "/api/experiments/WIP-0891-01/abort-review",
        json={"approve": True, "note": "確認終止"},
        headers=CHIEF,
    )
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "已終止"


def test_abort_review_reject_resumes(client):
    # 種子 WIP-0895-01 已有待主管判定的中止申請
    r = client.post(
        "/api/experiments/WIP-0895-01/abort-review",
        json={"approve": False, "note": "繼續"},
        headers=CHIEF,
    )
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "執行中"


def test_not_found_returns_404(client):
    r = client.get("/api/experiments/WIP-XXXX")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"


def test_machine_signal_triggers_completion(client):
    # WIP-0891-02 執行中 → 機台訊號（Celery eager 同步執行）→ 待確認
    r = client.post("/api/experiments/WIP-0891-02/machine-signal")
    assert r.status_code == 202
    after = client.get("/api/experiments/WIP-0891-02").json()["data"]
    assert after["status"] == "待確認"
    assert after["dataVerified"] is False  # 自動數據仍需人員驗證
    assert any(h["action"] == "機台自動數據蒐集" for h in after["history"])

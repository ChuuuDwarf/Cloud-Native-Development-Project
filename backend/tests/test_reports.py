"""實驗報告 API 測試（對應 test_module_D.md T-010）。"""

STAFF = {"X-Role": "staff"}
CHIEF = {"X-Role": "chief"}


def test_list_reports_seeded(client):
    r = client.get("/api/reports")
    assert r.status_code == 200
    assert r.json()["total"] == 2


def test_full_report_flow(client):
    # 從待確認的 WIP-0894-01 建立草稿
    r = client.post("/api/reports", json={"wipId": "WIP-0894-01"}, headers=STAFF)
    assert r.status_code == 200
    rid = r.json()["data"]["reportId"]
    assert r.json()["data"]["status"] == "草稿"

    # 編輯
    r = client.patch(f"/api/reports/{rid}", json={"conclusion": "數值在規格內"}, headers=STAFF)
    assert r.json()["data"]["conclusion"] == "數值在規格內"

    # 送審 → 待審核
    r = client.post(f"/api/reports/{rid}/submit", headers=STAFF)
    assert r.json()["data"]["status"] == "待審核"

    # 主管確認 → 已確認
    r = client.post(f"/api/reports/{rid}/review", json={"approve": True}, headers=CHIEF)
    assert r.json()["data"]["status"] == "已確認"

    # 發布 → 已回傳
    r = client.post(f"/api/reports/{rid}/publish", headers=STAFF)
    assert r.json()["data"]["status"] == "已回傳"
    assert len(r.json()["data"]["versions"]) >= 4


def test_create_report_allowed_for_chief(client):
    # 主管含實驗室人員權限，可建立報告
    r = client.post("/api/reports", json={"wipId": "WIP-0894-01"}, headers=CHIEF)
    assert r.status_code == 200


def test_create_report_forbidden_for_user(client):
    r = client.post("/api/reports", json={"wipId": "WIP-0894-01"}, headers={"X-Role": "user"})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN"


def test_review_forbidden_for_staff(client):
    r = client.post("/api/reports", json={"wipId": "WIP-0894-01"}, headers=STAFF)
    rid = r.json()["data"]["reportId"]
    client.post(f"/api/reports/{rid}/submit", headers=STAFF)
    r = client.post(f"/api/reports/{rid}/review", json={"approve": True}, headers=STAFF)
    assert r.status_code == 403


def test_review_rejects_to_revised(client):
    r = client.post("/api/reports", json={"wipId": "WIP-0894-01"}, headers=STAFF)
    rid = r.json()["data"]["reportId"]
    client.post(f"/api/reports/{rid}/submit", headers=STAFF)
    r = client.post(
        f"/api/reports/{rid}/review", json={"approve": False, "comment": "補數據"}, headers=CHIEF
    )
    assert r.json()["data"]["status"] == "已改版"


def test_report_not_found(client):
    r = client.get("/api/reports/RPT-XXXX")
    assert r.status_code == 404

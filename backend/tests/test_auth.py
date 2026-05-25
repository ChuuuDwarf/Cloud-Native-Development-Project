"""權限解析測試：JWT 主路徑 + X-Role 過渡 fallback。"""

import jwt

from app.config import JWT_ALG, JWT_ROLE_CLAIM, JWT_SECRET

CHECKIN = "/api/experiments/WIP-0892-01/check-in"
BODY = {"operator": "李工", "machineId": "OPT-001", "recipe": "RCP-OPT-v2.0"}


def _token(role_value: str) -> str:
    return jwt.encode({JWT_ROLE_CLAIM: role_value}, JWT_SECRET, algorithm=JWT_ALG)


def _bearer(role_value: str) -> dict:
    return {"Authorization": f"Bearer {_token(role_value)}"}


def test_jwt_staff_can_checkin(client):
    r = client.post(CHECKIN, json=BODY, headers=_bearer("staff"))
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "執行中"


def test_jwt_role_accepts_chinese_value(client):
    # claim 帶中文角色名也要能解析
    r = client.post(CHECKIN, json=BODY, headers=_bearer("實驗室人員"))
    assert r.status_code == 200


def test_jwt_chief_can_do_staff_action(client):
    # 主管含實驗室人員權限
    r = client.post(CHECKIN, json=BODY, headers=_bearer("chief"))
    assert r.status_code == 200


def test_jwt_user_forbidden_on_staff_action(client):
    r = client.post(CHECKIN, json=BODY, headers=_bearer("user"))
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN"


def test_invalid_token_returns_401(client):
    r = client.post(CHECKIN, json=BODY, headers={"Authorization": "Bearer not-a-jwt"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHORIZED"


def test_x_role_fallback_still_works(client):
    # 沒帶 Bearer → 退回 X-Role（過渡期）
    r = client.post(CHECKIN, json=BODY, headers={"X-Role": "staff"})
    assert r.status_code == 200

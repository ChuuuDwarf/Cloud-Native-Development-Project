import pytest
from dependencies import (
    can_view_all_labs,
    ensure_same_lab,
    get_user,
    lab_filter_sql,
    require_lab_scope,
    require_role,
)
from fastapi import HTTPException
from schemas import User


class _Result:
    def __init__(self, row):
        self.row = row

    def fetchone(self):
        return self.row


class _Conn:
    def __init__(self, row=None):
        self.row = row
        self.calls = []

    def execute(self, query, params=()):
        self.calls.append((query, params))
        return _Result(self.row)


def user(role="實驗室人員", lab="LAB A"):
    return User(
        userId="u-test",
        name="測試使用者",
        role=role,
        department="實驗室",
        lab=lab,
    )


def test_get_user_requires_header():
    with pytest.raises(HTTPException) as exc:
        get_user(_Conn(), None)

    assert exc.value.status_code == 401
    assert exc.value.detail == "X-User-Id header is required"


def test_get_user_rejects_unknown_user():
    with pytest.raises(HTTPException) as exc:
        get_user(_Conn(row=None), "missing")

    assert exc.value.status_code == 401
    assert exc.value.detail == "Unknown user"


def test_get_user_returns_serialized_user():
    conn = _Conn(
        {
            "user_id": "u-lab-a",
            "name": "林育誠",
            "role": "實驗室人員",
            "department": "實驗室",
            "lab": "LAB A",
        }
    )

    result = get_user(conn, "u-lab-a")

    assert result.userId == "u-lab-a"
    assert result.lab == "LAB A"
    assert conn.calls[0][1] == ("u-lab-a",)


def test_require_role_allows_permitted_role():
    require_role(user(), {"實驗室人員"})


def test_require_role_blocks_disallowed_role():
    with pytest.raises(HTTPException) as exc:
        require_role(user(role="廠區使用者", lab=None), {"實驗室人員"})

    assert exc.value.status_code == 403
    assert "cannot perform" in exc.value.detail


def test_global_roles_can_view_all_labs():
    assert can_view_all_labs(user(role="實驗室大主管", lab=None))
    assert can_view_all_labs(user(role="系統管理者", lab=None))
    assert not can_view_all_labs(user(role="實驗室人員"))


def test_require_lab_scope_returns_lab_for_lab_user():
    assert require_lab_scope(user(lab="LAB B")) == "LAB B"


def test_require_lab_scope_rejects_unscoped_user():
    with pytest.raises(HTTPException) as exc:
        require_lab_scope(user(role="系統管理者", lab=None))

    assert exc.value.status_code == 403


def test_lab_filter_sql_filters_lab_scoped_users():
    assert lab_filter_sql(user(lab="LAB C")) == (" WHERE lab = %s", ("LAB C",))
    assert lab_filter_sql(user(lab="LAB C"), "dispatches.lab") == (
        " WHERE dispatches.lab = %s",
        ("LAB C",),
    )


def test_lab_filter_sql_does_not_filter_global_users():
    assert lab_filter_sql(user(role="系統管理者", lab=None)) == ("", ())


def test_ensure_same_lab_blocks_cross_lab_access():
    with pytest.raises(HTTPException) as exc:
        ensure_same_lab(user(lab="LAB A"), "LAB B")

    assert exc.value.status_code == 403
    assert exc.value.detail == "Cannot access another lab"


def test_ensure_same_lab_allows_global_user():
    ensure_same_lab(user(role="系統管理者", lab=None), "LAB B")

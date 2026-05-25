"""
Unit test for apply_lab_scope
No DB hit - Only test the logic
We use User.lab_id and User.id as column args because they exist on main
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.common.dependencies import CurrentUser, apply_lab_scope
from app.common.errors import ForbiddenError
from app.db.models import User


def _make_user(
    *,
    role: str,
    permissions: list[str] | None = None,
    lab_id: uuid.UUID | None = None,
) -> CurrentUser:
    return CurrentUser(
        id=uuid.uuid4(),
        name="Test_User",
        email="test@example.com",
        role=role,
        permissions=permissions or [],
        lab_id=lab_id,
        department_id=None,
    )


def _has_where(stmt) -> bool:
    # Check if a statment has WHERE
    return len(stmt._where_criteria) > 0


def test_wildcard_permissions_returns_unfiltered_stmt() -> None:
    user = _make_user(role="anything_weird", permissions=["*"])
    stmt = select(User)
    out = apply_lab_scope(stmt, user, User.lab_id)
    assert _has_where(out) is False


def test_system_admin_role_returns_unfiltered_stmt() -> None:
    user = _make_user(role="system_admin", permissions=[])
    stmt = select(User)
    out = apply_lab_scope(stmt, user, User.lab_id)
    assert _has_where(out) is False


def test_engineer_with_lab_applies_lab_filter() -> None:
    lab_id = uuid.uuid4()
    user = _make_user(role="lab_engineer", lab_id=lab_id)
    stmt = select(User)
    out = apply_lab_scope(stmt, user, User.lab_id)

    assert _has_where(out) is True
    assert out.whereclause is not None
    compiled = out.whereclause.compile(compile_kwargs={"literal_binds": True})
    rendered = str(compiled)
    assert lab_id.hex in rendered


def test_engineer_without_lab_raises_forbidden() -> None:
    user = _make_user(role="lab_engineer", lab_id=None)
    stmt = select(User)

    with pytest.raises(ForbiddenError):
        apply_lab_scope(stmt, user, User.lab_id)


def test_supervisor_with_lab_applies_lab_filter() -> None:
    lab_id = uuid.uuid4()
    user = _make_user(role="lab_supervisor", lab_id=lab_id)
    stmt = select(User)
    out = apply_lab_scope(stmt, user, User.lab_id)

    assert _has_where(out) is True
    assert out.whereclause is not None
    compiled = out.whereclause.compile(compile_kwargs={"literal_binds": True})
    rendered = str(compiled)
    assert lab_id.hex in rendered


def test_supervisor_without_lab_raises_forbidden() -> None:
    user = _make_user(role="lab_supervisor", lab_id=None)
    stmt = select(User)

    with pytest.raises(ForbiddenError):
        apply_lab_scope(stmt, user, User.lab_id)


def test_plant_user_with_created_by_applies_owner_filter() -> None:
    user = _make_user(role="plant_user")
    stmt = select(User)
    out = apply_lab_scope(stmt, user, User.lab_id, created_by_column=User.id)

    assert _has_where(out) is True
    assert out.whereclause is not None
    compiled = out.whereclause.compile(compile_kwargs={"literal_binds": True})
    rendered = str(compiled)
    assert user.id.hex in rendered


def test_plant_user_without_created_by_raises_forbidden() -> None:
    user = _make_user(role="plant_user")
    stmt = select(User)

    with pytest.raises(ForbiddenError):
        apply_lab_scope(stmt, user, User.lab_id)


def test_unknown_role_raises_forbidden() -> None:
    user = _make_user(role="future_role", permissions=["something:read"])
    stmt = select(User)

    with pytest.raises(ForbiddenError):
        apply_lab_scope(stmt, user, User.lab_id)

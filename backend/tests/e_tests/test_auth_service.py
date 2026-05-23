"""Direct unit tests for ``AuthService`` and ``project_user``.

Covers the JWT round-trip + role/permission collapsing logic that the HTTP
layer otherwise hides.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.common.errors import UnauthorizedError
from app.core import database as db_module
from app.core.security import decode_access_token
from app.db.models import Role, User
from app.modules.auth.service import AuthService, project_user
from app.modules.users.schemas import UserUpdate
from app.modules.users.service import UserService


async def _load_user(email: str) -> User:
    async with db_module.AsyncSessionLocal() as session:
        row = await session.execute(
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .where(User.email == email)
        )
        return row.scalar_one()


@pytest.mark.asyncio
async def test_authenticate_returns_user_on_correct_password() -> None:
    async with db_module.AsyncSessionLocal() as session:
        service = AuthService(session)
        user = await service.authenticate("admin@example.com", "Admin1234")
    assert user.email == "admin@example.com"


@pytest.mark.asyncio
async def test_authenticate_wrong_password_raises_unauthorized() -> None:
    async with db_module.AsyncSessionLocal() as session:
        service = AuthService(session)
        with pytest.raises(UnauthorizedError):
            await service.authenticate("admin@example.com", "WrongPassword!")


@pytest.mark.asyncio
async def test_authenticate_unknown_email_raises_unauthorized() -> None:
    async with db_module.AsyncSessionLocal() as session:
        service = AuthService(session)
        with pytest.raises(UnauthorizedError):
            await service.authenticate("nobody@example.com", "Whatever1234")


@pytest.mark.asyncio
async def test_authenticate_disabled_user_raises_unauthorized() -> None:
    # Create then disable a throwaway account so we don't break the seeded set.
    async with db_module.AsyncSessionLocal() as session:
        created = await UserService(session).create_user(
            __import__("app.modules.users.schemas", fromlist=["UserCreate"]).UserCreate(
                email="auth-disabled@example.com",
                name="Disabled User",
                password="GoodPass1234",
            )
        )
        target_id = created.id

    from app.common.enums import UserStatus

    async with db_module.AsyncSessionLocal() as session:
        await UserService(session).update_user(target_id, UserUpdate(status=UserStatus.DISABLED))

    async with db_module.AsyncSessionLocal() as session:
        service = AuthService(session)
        with pytest.raises(UnauthorizedError):
            await service.authenticate("auth-disabled@example.com", "GoodPass1234")


@pytest.mark.asyncio
async def test_issue_token_round_trips_through_decode() -> None:
    user = await _load_user("admin@example.com")
    token = AuthService.issue_token(user)
    decoded = decode_access_token(token)
    assert decoded["sub"] == str(user.id)
    assert decoded["email"] == "admin@example.com"
    assert decoded["name"] == user.name


@pytest.mark.asyncio
async def test_project_user_admin_has_wildcard() -> None:
    user = await _load_user("admin@example.com")
    role, permissions = project_user(user)
    assert role == "system_admin"
    assert "*" in permissions


@pytest.mark.asyncio
async def test_project_user_plant_user_has_scoped_permissions() -> None:
    user = await _load_user("requester@example.com")
    role, permissions = project_user(user)
    assert role == "plant_user"
    assert "*" not in permissions
    # sorted, deduplicated union
    assert permissions == sorted(set(permissions))
    assert "orders:create" in permissions
    assert "users:create" not in permissions


@pytest.mark.asyncio
async def test_project_user_collapses_multiple_roles() -> None:
    """A user with two roles should see the union of their permissions and the
    first role's name as the primary role.
    """
    from app.modules.users.schemas import UserCreate

    # Look up both role IDs.
    async with db_module.AsyncSessionLocal() as session:
        rows = (
            (
                await session.execute(
                    select(Role).where(Role.name.in_(["lab_engineer", "plant_user"]))
                )
            )
            .scalars()
            .all()
        )
        role_ids = [r.id for r in rows]

    async with db_module.AsyncSessionLocal() as session:
        created = await UserService(session).create_user(
            UserCreate(
                email="multi-role@example.com",
                name="Multi Role",
                password="StrongPass123",
                roleIds=role_ids,
            )
        )
        target_id = created.id

    full_user = await _load_user("multi-role@example.com")
    role, permissions = project_user(full_user)
    assert role in {"lab_engineer", "plant_user"}
    # plant_user.orders:create AND lab_engineer.experiment_runs:execute both
    # present -> proves the union actually unioned.
    assert "orders:create" in permissions
    assert "experiment_runs:execute" in permissions
    assert "*" not in permissions

    assert target_id  # silence unused warning

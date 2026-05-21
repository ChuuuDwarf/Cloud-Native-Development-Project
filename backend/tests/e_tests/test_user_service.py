"""Direct unit tests for ``UserService`` (no HTTP layer).

These cover the gaps the API-level tests can't reach efficiently — invalid
role IDs, password reset paths, role replacement, NotFoundError, etc.
Each test opens its own ``AsyncSession`` against the seeded test DB.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from app.common.enums import UserStatus
from app.common.errors import ConflictError, NotFoundError, ValidationError
from app.core import database as db_module
from app.db.models import Role, User
from app.modules.users.schemas import UserCreate, UserUpdate
from app.modules.users.service import UserService


async def _engineer_role_id() -> uuid.UUID:
    async with db_module.AsyncSessionLocal() as session:
        row = await session.execute(select(Role).where(Role.name == "lab_engineer"))
        return row.scalar_one().id


async def _find_user_id(email: str) -> uuid.UUID:
    async with db_module.AsyncSessionLocal() as session:
        row = await session.execute(select(User).where(User.email == email))
        return row.scalar_one().id


@pytest.mark.asyncio
async def test_create_user_happy_path_assigns_roles_and_hashes_password() -> None:
    engineer_role_id = await _engineer_role_id()
    async with db_module.AsyncSessionLocal() as session:
        service = UserService(session)
        payload = UserCreate(
            email="svc-create@example.com",
            name="Service Create",
            password="StrongPass123",
            roleIds=[engineer_role_id],
        )
        created = await service.create_user(payload)

    assert created.email == "svc-create@example.com"
    assert created.status == UserStatus.ACTIVE
    assert created.is_active is True
    assert created.password_hash != "StrongPass123", "password must be hashed"
    assert {r.id for r in created.roles} == {engineer_role_id}


@pytest.mark.asyncio
async def test_create_user_duplicate_email_raises_conflict() -> None:
    async with db_module.AsyncSessionLocal() as session:
        service = UserService(session)
        payload = UserCreate(
            email="admin@example.com",  # seeded
            name="Dup",
            password="WhateverGoes1",
        )
        with pytest.raises(ConflictError):
            await service.create_user(payload)


@pytest.mark.asyncio
async def test_create_user_invalid_role_ids_raises_validation_error() -> None:
    async with db_module.AsyncSessionLocal() as session:
        service = UserService(session)
        ghost = uuid.uuid4()
        payload = UserCreate(
            email="svc-bad-role@example.com",
            name="Bad Role",
            password="StrongPass123",
            roleIds=[ghost],
        )
        with pytest.raises(ValidationError):
            await service.create_user(payload)


@pytest.mark.asyncio
async def test_update_user_changes_name_status_and_password() -> None:
    # Create a dedicated victim — keep the four seed users pristine.
    async with db_module.AsyncSessionLocal() as session:
        target = await UserService(session).create_user(
            UserCreate(
                email="svc-update@example.com",
                name="Update Me",
                password="OriginalPass1",
            )
        )
        original_hash = target.password_hash
        target_id = target.id

    async with db_module.AsyncSessionLocal() as session:
        service = UserService(session)
        updated = await service.update_user(
            target_id,
            UserUpdate(
                name="Updated Name",
                status=UserStatus.DISABLED,
                password="BrandNewPass2",
            ),
        )

    assert updated.name == "Updated Name"
    assert updated.status == UserStatus.DISABLED
    assert updated.is_active is False
    assert updated.password_hash != original_hash, "password hash must change"


@pytest.mark.asyncio
async def test_update_user_replaces_roles() -> None:
    engineer_role_id = await _engineer_role_id()
    async with db_module.AsyncSessionLocal() as session:
        target = await UserService(session).create_user(
            UserCreate(
                email="svc-role-swap@example.com",
                name="Role Swap",
                password="OriginalPass1",
                roleIds=[],
            )
        )
        target_id = target.id

    async with db_module.AsyncSessionLocal() as session:
        updated = await UserService(session).update_user(
            target_id, UserUpdate(roleIds=[engineer_role_id])
        )
    assert {r.id for r in updated.roles} == {engineer_role_id}

    # Replace with the empty list and confirm roles are cleared.
    async with db_module.AsyncSessionLocal() as session:
        cleared = await UserService(session).update_user(target_id, UserUpdate(roleIds=[]))
    assert cleared.roles == []


@pytest.mark.asyncio
async def test_find_user_by_id_missing_raises_not_found() -> None:
    async with db_module.AsyncSessionLocal() as session:
        service = UserService(session)
        with pytest.raises(NotFoundError):
            await service.find_user_by_id(uuid.uuid4())


@pytest.mark.asyncio
async def test_update_user_with_invalid_role_ids_raises_validation_error() -> None:
    user_id = await _find_user_id("admin@example.com")
    async with db_module.AsyncSessionLocal() as session:
        service = UserService(session)
        with pytest.raises(ValidationError):
            await service.update_user(user_id, UserUpdate(roleIds=[uuid.uuid4()]))

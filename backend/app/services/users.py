"""Business logic for /api/users."""

import uuid
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums import UserStatus
from app.common.errors import ConflictError, NotFoundError, ValidationError
from app.core.database import get_db
from app.core.security import hash_password
from app.db.models import User
from app.repos.user_repo import UserRepository
from app.schemas.users import UserCreate, UserQuery, UserUpdate


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = UserRepository(session)

    async def find_users(
        self,
        *,
        offset: int,
        limit: int,
        query: UserQuery | None = None,
    ) -> tuple[list[User], int]:
        q = query or UserQuery()
        items, total = await self._repo.list_users(
            offset=offset,
            limit=limit,
            keyword=q.keyword,
            role_name=q.role,
            department_id=q.department_id,
            lab_id=q.lab_id,
            status=q.status,
        )
        return list(items), total

    async def find_user_by_id(self, user_id: uuid.UUID) -> User:
        user = await self._repo.find_by_id(user_id)
        if user is None:
            raise NotFoundError(f"User {user_id} not found")
        return user

    async def create_user(self, payload: UserCreate) -> User:
        if await self._repo.find_by_email(str(payload.email)):
            raise ConflictError(f"Email {payload.email} is already in use")

        roles = await self._resolve_roles(payload.role_ids)

        user = User(
            email=str(payload.email),
            name=payload.name,
            password_hash=hash_password(payload.password),
            department_id=payload.department_id,
            lab_id=payload.lab_id,
            status=UserStatus.ACTIVE,
            is_active=True,
        )
        user.roles = roles
        created = await self._repo.add(user)
        await self._session.commit()
        await self._session.refresh(created)
        # Re-fetch with full relationships so the response includes roles + perms
        fresh = await self._repo.find_by_id(created.id)
        assert fresh is not None
        return fresh

    async def update_user(self, user_id: uuid.UUID, payload: UserUpdate) -> User:
        user = await self.find_user_by_id(user_id)

        if payload.name is not None:
            user.name = payload.name
        if payload.department_id is not None:
            user.department_id = payload.department_id
        if payload.lab_id is not None:
            user.lab_id = payload.lab_id
        if payload.status is not None:
            user.status = payload.status
            user.is_active = payload.status == UserStatus.ACTIVE
        if payload.role_ids is not None:
            user.roles = await self._resolve_roles(payload.role_ids)
        if payload.password is not None:
            user.password_hash = hash_password(payload.password)

        await self._session.flush()
        await self._session.commit()

        refreshed = await self._repo.find_by_id(user.id)
        assert refreshed is not None
        return refreshed

    async def _resolve_roles(self, role_ids: list[uuid.UUID]):
        if not role_ids:
            return []
        roles = await self._repo.find_roles_by_ids(role_ids)
        missing = set(role_ids) - {r.id for r in roles}
        if missing:
            raise ValidationError(f"Unknown role ids: {sorted(str(m) for m in missing)}")
        return roles


def get_user_service(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> UserService:
    return UserService(session)

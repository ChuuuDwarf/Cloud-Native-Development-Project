"""DB access for users — supports keyword / role / department / lab / status filters."""

import uuid
from collections.abc import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.enums import UserStatus
from app.db.models import Role, User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self._session.execute(
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def find_by_email(self, email: str) -> User | None:
        result = await self._session.execute(
            select(User).options(selectinload(User.roles)).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def list_users(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
        keyword: str | None = None,
        role_name: str | None = None,
        department_id: uuid.UUID | None = None,
        lab_id: uuid.UUID | None = None,
        status: UserStatus | None = None,
    ) -> tuple[Sequence[User], int]:
        stmt = (
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .order_by(User.created_at.desc())
        )

        if keyword:
            pattern = f"%{keyword.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(User.email).like(pattern),
                    func.lower(User.name).like(pattern),
                )
            )
        if department_id is not None:
            stmt = stmt.where(User.department_id == department_id)
        if lab_id is not None:
            stmt = stmt.where(User.lab_id == lab_id)
        if status is not None:
            stmt = stmt.where(User.status == status)
        if role_name:
            stmt = stmt.where(User.roles.any(Role.name == role_name))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self._session.execute(count_stmt)).scalar_one()

        rows = await self._session.execute(stmt.offset(offset).limit(limit))
        items = rows.scalars().unique().all()
        return items, total

    async def find_roles_by_ids(self, role_ids: list[uuid.UUID]) -> list[Role]:
        if not role_ids:
            return []
        result = await self._session.execute(select(Role).where(Role.id.in_(role_ids)))
        return list(result.scalars().all())

    async def add(self, user: User) -> User:
        self._session.add(user)
        await self._session.flush()
        return user

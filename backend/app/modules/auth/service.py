"""AuthService — bcrypt verify + JWT issuance + role/permission projection."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.errors import UnauthorizedError
from app.core.security import create_access_token, verify_password
from app.db.models import Role, User


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def authenticate(self, email: str, password: str) -> User:
        user = await self._load_user_by(User.email == email)
        if user is None or not verify_password(password, user.password_hash):
            raise UnauthorizedError("Invalid email or password")
        if not user.is_active:
            raise UnauthorizedError("Account is disabled")
        return user

    async def find_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self._load_user_by(User.id == user_id)

    async def _load_user_by(self, predicate) -> User | None:
        result = await self._session.execute(
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .where(predicate)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def issue_token(user: User) -> str:
        return create_access_token(
            subject=str(user.id),
            extra={
                "name": user.name,
                "email": user.email,
            },
        )


def project_user(user: User) -> tuple[str, list[str]]:
    """Collapse user.roles[].permissions[] into (primary_role_name, sorted_permission_codes)."""
    perms: set[str] = set()
    primary_role = ""
    for role in user.roles:
        if not primary_role:
            primary_role = role.name
        for perm in role.permissions:
            perms.add(perm.code)
    return primary_role, sorted(perms)

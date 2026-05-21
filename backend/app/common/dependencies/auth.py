"""Auth dependencies — `Depends(get_current_user)` and `Depends(require_permission(...))`.

Phase 1 implementation: reads the `access_token` httpOnly cookie issued by
``/api/auth/login``, decodes the JWT, loads the User from the DB (with roles +
permissions eager-loaded), and projects it into a lightweight ``CurrentUser``.

Raises ``UnauthorizedError`` if the cookie is missing or the JWT is invalid /
expired / refers to an unknown or disabled user.
"""

import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import Cookie, Depends
from jose import JWTError
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.errors import ForbiddenError, UnauthorizedError
from app.core.database import get_db
from app.core.security import decode_access_token


class CurrentUser(BaseModel):
    """The shape endpoints rely on for auth decisions.

    `permissions` is the deduplicated, sorted union of every permission code
    granted by the user's roles. A user with the magic ``*`` permission
    bypasses every ``require_permission(...)`` check.
    """

    id: uuid.UUID
    name: str
    email: str
    role: str
    permissions: list[str]
    lab_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None


async def get_current_user(
    session: Annotated[AsyncSession, Depends(get_db)],
    access_token: Annotated[str | None, Cookie(alias="access_token")] = None,
) -> CurrentUser:
    if not access_token:
        raise UnauthorizedError("Authentication required")

    try:
        payload = decode_access_token(access_token)
    except JWTError as exc:
        raise UnauthorizedError("Invalid or expired token") from exc

    sub = payload.get("sub")
    if not sub:
        raise UnauthorizedError("Token missing subject")

    try:
        user_id = uuid.UUID(sub)
    except ValueError as exc:
        raise UnauthorizedError("Token subject is not a valid user id") from exc

    # Import lazily so common/dependencies stays free of module-level DB deps.
    from app.modules.auth.service import AuthService, project_user

    user = await AuthService(session).find_by_id(user_id)
    if user is None:
        raise UnauthorizedError("User no longer exists")
    if not user.is_active:
        raise UnauthorizedError("Account is disabled")

    role, permissions = project_user(user)
    return CurrentUser(
        id=user.id,
        name=user.name,
        email=user.email,
        role=role,
        permissions=permissions,
        lab_id=user.lab_id,
        department_id=user.department_id,
    )


def require_permission(code: str) -> Callable[..., CurrentUser]:
    """Dependency factory: gate a route on a permission code.

    Usage::

        @router.post(
            "/users",
            dependencies=[Depends(require_permission("users:create"))],
        )
        async def create_user(...): ...

    Or accept the user as a parameter::

        async def update_user(
            ...,
            user: Annotated[CurrentUser, Depends(require_permission("users:update"))],
        ): ...
    """

    async def _checker(
        user: Annotated[CurrentUser, Depends(get_current_user)],
    ) -> CurrentUser:
        if "*" in user.permissions or code in user.permissions:
            return user
        raise ForbiddenError(f"Missing required permission: {code}")

    return _checker


__all__ = ["CurrentUser", "get_current_user", "require_permission"]

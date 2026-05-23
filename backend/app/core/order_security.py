from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from app.common.dependencies import CurrentUser

# The order module used to check legacy mock roles such as site_user/lab_manager.
# Keep those business names as aliases, but resolve them from the real auth user
# returned by /api/me instead of app.data.master_data.USERS.
ROLE_ALIASES: dict[str, set[str]] = {
    "site_user": {"site_user", "plant_user", "system_admin"},
    "lab_manager": {"lab_manager", "lab_supervisor", "system_admin"},
    "lab_staff": {"lab_staff", "lab_engineer", "lab_supervisor", "system_admin"},
    "admin": {"admin", "system_admin"},
}

PERMISSION_ALIASES: dict[str, set[str]] = {
    "site_user": {"orders:create"},
    "lab_manager": {"orders:approve"},
    "lab_staff": {"orders:read"},
    "admin": {"*"},
}


def user_id(user: CurrentUser) -> str:
    return str(user.id)


def _expand_roles(roles: set[str]) -> set[str]:
    expanded: set[str] = set()
    for role in roles:
        expanded.update(ROLE_ALIASES.get(role, {role}))
    return expanded


def _expand_permissions(roles: set[str]) -> set[str]:
    expanded: set[str] = set()
    for role in roles:
        expanded.update(PERMISSION_ALIASES.get(role, set()))
    return expanded


def require_role(user: CurrentUser, roles: set[str]) -> dict[str, Any]:
    """Authorize the logged-in user for an order workflow role.

    The old implementation accepted a user id and looked it up in mock
    master_data.USERS. This version accepts the real authenticated user from
    /api/me and checks either its role name or permissions.
    """

    accepted_roles = _expand_roles(roles)
    accepted_permissions = _expand_permissions(roles)

    has_role = user.role in accepted_roles
    has_permission = "*" in user.permissions or bool(accepted_permissions.intersection(user.permissions))

    if not (has_role or has_permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User {user.id} does not have required role: {', '.join(sorted(roles))}",
        )

    lab_ids = [str(user.lab_id)] if user.lab_id is not None else []
    return {
        "id": str(user.id),
        "name": user.name,
        "role": user.role,
        "permissions": user.permissions,
        "labIds": lab_ids,
        "departmentId": str(user.department_id) if user.department_id is not None else None,
    }

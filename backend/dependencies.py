from typing import Any

from fastapi import HTTPException

from schemas import User, UserRole
from serializers import user_from_row


def get_user(conn: Any, user_id: str | None) -> User:
    if not user_id:
        raise HTTPException(status_code=401, detail="X-User-Id header is required")
    row = conn.execute("SELECT * FROM users WHERE user_id = %s", (user_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="Unknown user")
    return user_from_row(row)


def require_role(user: User, allowed_roles: set[UserRole]) -> None:
    if user.role not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail=f"{user.role} cannot perform this role C operation",
        )


def can_view_all_labs(user: User) -> bool:
    return user.role in {"實驗室大主管", "系統管理者"}


def require_lab_scope(user: User) -> str:
    if not user.lab:
        raise HTTPException(
            status_code=403, detail="This operation requires a lab-scoped user"
        )
    return user.lab


def lab_filter_sql(user: User, column: str = "lab") -> tuple[str, tuple[object, ...]]:
    if can_view_all_labs(user):
        return "", ()
    return f" WHERE {column} = %s", (require_lab_scope(user),)


def ensure_same_lab(user: User, lab: str) -> None:
    if can_view_all_labs(user):
        return
    if lab != require_lab_scope(user):
        raise HTTPException(status_code=403, detail="Cannot access another lab")

from app.common.dependencies.auth import (
    CurrentUser,
    get_current_user,
    require_permission,
)
from app.common.dependencies.pagination import PaginationParams, get_pagination
from app.common.dependencies.scope import apply_lab_scope

__all__ = [
    "CurrentUser",
    "PaginationParams",
    "apply_lab_scope",
    "get_current_user",
    "get_pagination",
    "require_permission",
]

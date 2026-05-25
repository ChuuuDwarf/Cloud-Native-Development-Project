"""Row-level scoping helper for lab / owner filters.

Each protected endpoint can build a SQLAlchemy ``select()`` and call
:func:`apply_lab_scope` to attach the right WHERE clause based on the
caller's role. Centralising the rule here keeps every module's repository
queries consistent with the role matrix in ``docs/role.md``:

==============  ============================================================
Role            Filter applied
==============  ============================================================
system_admin    none — sees everything
lab_engineer    ``lab_id_column == user.lab_id``
lab_supervisor  ``lab_id_column == user.lab_id`` (same as engineer)
plant_user      ``created_by_column == user.id`` (own records only); raises
                ``ForbiddenError`` if no ``created_by_column`` is supplied
==============  ============================================================

Anything else (unknown role, missing ``lab_id`` for a lab-bound role)
raises :class:`ForbiddenError` rather than silently leaking rows.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Select

from app.common.dependencies.auth import CurrentUser
from app.common.errors import ForbiddenError


def apply_lab_scope(
    stmt: Select[Any],
    user: CurrentUser,
    lab_id_column: Any,
    *,
    created_by_column: Any = None,
) -> Select[Any]:
    """Add a row-level scope filter to ``stmt`` based on ``user.role``.

    Parameters
    ----------
    stmt
        The select statement to scope.
    user
        The authenticated caller (from ``get_current_user``).
    lab_id_column
        The SQLAlchemy column on the queried entity that holds the lab id
        the row belongs to. Used for engineer / supervisor scoping.
    created_by_column
        Optional column holding the creator's user id. Required when the
        caller is ``plant_user``; if absent, plant_user is denied with
        :class:`ForbiddenError` (the resource is not exposed to them).

    Returns
    -------
    Select[Any]
        The same statement with the appropriate ``.where(...)`` applied.

    Raises
    ------
    ForbiddenError
        If the caller has a lab-bound role without a ``lab_id`` set, is a
        plant_user trying to access a resource that has no owner column to
        filter on, or carries a role string that isn't mapped here.
    """
    if "*" in user.permissions:
        return stmt

    role = user.role
    if role == "system_admin":
        return stmt

    if role in ("lab_supervisor", "lab_engineer"):
        if user.lab_id is None:
            raise ForbiddenError(f"User has role {role!r} but no lab assignment")
        return stmt.where(lab_id_column == user.lab_id)

    if role == "plant_user":
        if created_by_column is None:
            raise ForbiddenError("plant_user is not permitted to view this resource")
        return stmt.where(created_by_column == user.id)

    raise ForbiddenError(f"Role {role!r} is not permitted to view this resource")


__all__ = ["apply_lab_scope"]

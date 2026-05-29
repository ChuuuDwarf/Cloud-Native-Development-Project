"""Row-level scoping helper for lab / owner filters.

Each protected endpoint can build a SQLAlchemy ``select()`` and call
:func:`apply_lab_scope` to attach the right WHERE clause based on the
caller's role. Centralising the rule here keeps every module's repository
queries consistent with the role matrix in ``docs/role.md``:

==================  ============================================================
Role                Filter applied
==================  ============================================================
system_admin        none — sees everything
general_supervisor  none — 大主管 oversees every lab. Used by ``apply_lab_scope``
                    for read-side row visibility; write paths that need to know
                    which labs the actor is allowed in (e.g. order approval)
                    check ``order_security.ALL_LABS_ROLES`` separately.
lab_engineer        ``lab_id_column == user.lab_id``
lab_supervisor      ``lab_id_column == user.lab_id`` (same as engineer)
plant_user          ``created_by_column == user.id`` (own records only); raises
                    ``ForbiddenError`` if no ``created_by_column`` is supplied
==================  ============================================================

Anything else (unknown role, missing ``lab_id`` for a lab-bound role)
raises :class:`ForbiddenError` rather than silently leaking rows.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies.auth import CurrentUser
from app.common.errors import ForbiddenError
from app.db.models.labs import Lab


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
    if role in ("system_admin", "general_supervisor"):
        # general_supervisor (大主管) is intentionally treated like an admin
        # for *read* paths: the dashboard / issues list / notifications etc.
        # need cross-lab visibility. Write authorisation is still gated by
        # per-endpoint permission checks (require_permission), so this does
        # not grant them broader mutate rights than lab_supervisor.
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


async def resolve_user_lab_codes(session: AsyncSession, user: CurrentUser) -> list[str] | None:
    """Return the list of lab codes (e.g. ``["LAB-A"]``) this user may see,
    or ``None`` to mean "all labs / no filter".

    For models whose lab column is a String code (Machine.lab,
    OrderItemModel.lab_id, Wip.lab_name, Dispatch.lab) — apply_lab_scope
    can't help because it expects a UUID FK. Caller does::

        codes = await resolve_user_lab_codes(session, user)
        if codes is not None:
            stmt = stmt.where(Machine.lab.in_(codes))

    Returns ``None`` for system_admin / general_supervisor (cross-lab).
    Returns a single-element list for lab_supervisor / lab_engineer.
    Raises ForbiddenError for plant_user (never has lab-scoped access to
    machine / order data through this helper).
    """
    if "*" in user.permissions or user.role in ("system_admin", "general_supervisor"):
        return None

    if user.role in ("lab_supervisor", "lab_engineer"):
        if user.lab_id is None:
            raise ForbiddenError(f"User has role {user.role!r} but no lab assignment")
        code = (
            await session.execute(select(Lab.code).where(Lab.id == user.lab_id))
        ).scalar_one_or_none()
        if code is None:
            raise ForbiddenError(f"Lab {user.lab_id} not found")
        return [code]

    raise ForbiddenError(f"Role {user.role!r} is not permitted to view this resource")


__all__ = ["apply_lab_scope", "resolve_user_lab_codes"]

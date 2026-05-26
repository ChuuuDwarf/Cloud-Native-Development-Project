"""Shared recipient-lookup helpers for notification fan-out.

Used by both ``IssueService`` (initial notify on create) and the Celery
escalation worker (per-level notify). Kept in ``app/common/`` because it
crosses module boundaries (users + roles) and has no business policy of
its own — just "give me the user ids who hold this role in this lab".
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.roles import Role
from app.db.models.users import User


async def recipients_for_role_in_lab(
    session: AsyncSession,
    *,
    lab_id: UUID,
    role_name: str,
) -> list[UUID]:
    """All user ids holding ``role_name`` inside ``lab_id``.

    ``User.lab_id == lab_id`` intentionally excludes lab-less users (e.g.
    ``system_admin``), so global accounts never get per-lab spam.
    """
    stmt = select(User.id).join(User.roles).where(User.lab_id == lab_id, Role.name == role_name)
    result = await session.execute(stmt)
    return list(result.scalars().all())

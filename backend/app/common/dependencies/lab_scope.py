"""Lab/factory scoping for 組員 D's modules (experiment_runs / reports / closures).

D operates on B's ``wips`` table, whose ``lab_name`` column stores the lab's
display name (``labs.name``, e.g. ``電性測試實驗室``). The auth ``CurrentUser``
only carries ``lab_id`` (UUID), so we resolve it once to the lab name and
compare against ``wips.lab_name`` — mirroring how B's ``wip_service`` /
``transfer_service`` scope visibility by ``lab_name``.

Scoping rule (satisfies the requested "非此 lab 看不到此單" lab isolation):

- ``system_admin``                       → sees every lab
- ``lab_supervisor`` / ``lab_engineer``  → only their own lab
- a non-admin user without a lab         → sees nothing

This module is intentionally NOT re-exported from ``app.common.dependencies``'s
``__init__`` so that package stays free of module-level ``app.db.models``
imports (see the note in ``auth.py``). Import it directly where needed.
See [[cd-yields-to-ab-models]].
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies.auth import CurrentUser
from app.db.models import Lab


@dataclass(frozen=True)
class LabScope:
    """Resolved lab-visibility context for the current request."""

    role: str
    lab_name: str | None

    @classmethod
    def system(cls) -> LabScope:
        """An unrestricted scope for system/background contexts (e.g. Celery)."""
        return cls(role="system_admin", lab_name=None)

    @property
    def sees_all_labs(self) -> bool:
        return self.role == "system_admin"

    def can_access_lab(self, target_lab: str | None) -> bool:
        """Whether the user may see/operate on a row belonging to ``target_lab``."""
        if self.sees_all_labs:
            return True
        if not self.lab_name:
            return False
        return target_lab == self.lab_name

    def list_lab_filter(self) -> str | None:
        """The ``lab_name`` to filter list queries by, or ``None`` for "all labs".

        Callers must first short-circuit to an empty result when the user is
        restricted but has no lab (``restricted_without_lab``); otherwise a
        ``None`` here would wrongly mean "see everything".
        """
        return None if self.sees_all_labs else self.lab_name

    @property
    def restricted_without_lab(self) -> bool:
        """A non-admin who has no lab — they should see nothing."""
        return not self.sees_all_labs and not self.lab_name


async def resolve_lab_name(db: AsyncSession, lab_id: uuid.UUID | None) -> str | None:
    if lab_id is None:
        return None
    result = await db.execute(select(Lab.name).where(Lab.id == lab_id))
    return result.scalars().first()


async def build_lab_scope(user: CurrentUser, db: AsyncSession) -> LabScope:
    lab_name = await resolve_lab_name(db, user.lab_id)
    return LabScope(role=user.role, lab_name=lab_name)

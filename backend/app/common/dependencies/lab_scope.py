"""Lab/factory scoping for 組員 D's modules (experiment_runs / reports / closures)
and 組員 C's modules (machines / dispatches).

D's tables (``wips`` etc.) store the lab's **display name** in ``lab_name``
(``labs.name``, e.g. ``電性測試實驗室``).
C's tables (``machines.lab``, ``dispatches.lab``) store the **short code**
(``labs.code``, e.g. ``LAB-A``).

The auth ``CurrentUser`` only carries ``lab_id`` (UUID), so we resolve it
once to *both* the lab name and code and let each caller pick the one that
matches its column. A single canonical column would have been preferable
but is not where the legacy data sits.

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
    """Resolved lab-visibility context for the current request.

    ``lab_name`` matches D's ``lab_name`` columns (Chinese display string).
    ``lab_code`` matches C's ``lab`` columns (short code, e.g. ``LAB-A``).
    """

    role: str
    lab_name: str | None
    lab_code: str | None = None

    @classmethod
    def system(cls) -> LabScope:
        """An unrestricted scope for system/background contexts (e.g. Celery)."""
        return cls(role="system_admin", lab_name=None, lab_code=None)

    @property
    def sees_all_labs(self) -> bool:
        return self.role == "system_admin"

    def can_access_lab(self, target_lab: str | None) -> bool:
        """Whether the user may see/operate on a row whose ``lab`` column matches.

        Matches ``target_lab`` against EITHER ``lab_name`` or ``lab_code``, so the
        same scope object works for D's ``lab_name``-keyed rows and C's
        ``lab_code``-keyed rows without the caller having to pick.
        """
        if self.sees_all_labs:
            return True
        if not self.lab_name and not self.lab_code:
            return False
        return target_lab == self.lab_name or target_lab == self.lab_code

    def list_lab_filter(self) -> str | None:
        """The ``lab_name`` (D-style) to filter list queries by, or ``None`` for "all labs".

        Callers must first short-circuit to an empty result when the user is
        restricted but has no lab (``restricted_without_lab``); otherwise a
        ``None`` here would wrongly mean "see everything".
        """
        return None if self.sees_all_labs else self.lab_name

    def list_lab_code_filter(self) -> str | None:
        """The ``lab_code`` (C-style) to filter list queries by, or ``None`` for "all labs"."""
        return None if self.sees_all_labs else self.lab_code

    @property
    def restricted_without_lab(self) -> bool:
        """A non-admin who has no lab — they should see nothing."""
        return not self.sees_all_labs and not self.lab_name and not self.lab_code


async def resolve_lab(db: AsyncSession, lab_id: uuid.UUID | None) -> tuple[str | None, str | None]:
    """Resolve a lab_id to (name, code). Returns (None, None) if not found."""
    if lab_id is None:
        return None, None
    result = await db.execute(select(Lab.name, Lab.code).where(Lab.id == lab_id))
    row = result.first()
    if row is None:
        return None, None
    return row.name, row.code


async def resolve_lab_name(db: AsyncSession, lab_id: uuid.UUID | None) -> str | None:
    """Backwards-compat: name-only resolver retained for callers that only need name."""
    name, _ = await resolve_lab(db, lab_id)
    return name


async def build_lab_scope(user: CurrentUser, db: AsyncSession) -> LabScope:
    lab_name, lab_code = await resolve_lab(db, user.lab_id)
    return LabScope(role=user.role, lab_name=lab_name, lab_code=lab_code)

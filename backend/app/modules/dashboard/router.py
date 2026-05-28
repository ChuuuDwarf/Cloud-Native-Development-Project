"""Dashboard HTTP routes.

* ``GET /api/dashboard``        — one-shot snapshot. The frontend polls every
  30s via TanStack Query.
* ``GET /api/dashboard/stream`` — SSE channel. Yields event-name lines (no
  payload) so the FE invalidates the ``["dashboard"]`` query and re-fetches
  the full snapshot.

The endpoint is gated by ``dashboard:read``; the seeded ``general_supervisor``,
``lab_supervisor``, and ``system_admin`` roles all hold it.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sse_starlette.sse import EventSourceResponse

from app.common.dependencies import CurrentUser, get_current_user, require_permission
from app.common.schemas import ApiResponse
from app.core.database import AsyncSessionLocal
from app.db.models.labs import Lab
from app.modules.dashboard.dependencies import get_dashboard_service
from app.modules.dashboard.publisher import listen
from app.modules.dashboard.schemas import DashboardSnapshot
from app.modules.dashboard.service import DashboardService

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("", response_model=ApiResponse[DashboardSnapshot])
async def get_dashboard(
    service: Annotated[DashboardService, Depends(get_dashboard_service)],
    user: Annotated[CurrentUser, Depends(require_permission("dashboard:read"))],
) -> ApiResponse[DashboardSnapshot]:
    """Return a complete dashboard snapshot for the caller.

    The same envelope shape is returned for every role; widgets the role
    doesn't apply to come back as ``None``. Lab scoping is derived from the
    caller, not a query param, so there's no way for a lab_supervisor to
    request another lab's view.
    """
    snapshot = await service.compute_snapshot(user)
    return ApiResponse(data=snapshot)


@router.get("/stream", dependencies=[Depends(require_permission("dashboard:read"))])
async def stream_dashboard(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> EventSourceResponse:
    """Subscribe to dashboard invalidation events for this caller's scope.

    Channels:

    * ``dashboard:events:global`` — every caller listens here so global
      events (e.g. an escalation in any lab) always reach the page.
    * ``dashboard:events:{lab_code}`` — added for lab_bound roles so
      per-lab fanouts are received without flooding global subscribers.

    The handler yields event-name strings; the FE only needs the *signal*,
    not the payload, since it re-fetches the full snapshot after each one.
    """
    channels = ["dashboard:events:global"]
    if user.role in ("lab_supervisor", "lab_engineer") and user.lab_id is not None:
        # Resolve the user's lab code so we subscribe to the right per-lab
        # channel. Using a one-shot session here (not the request session)
        # because the SSE generator outlives the request scope.
        async with AsyncSessionLocal() as session:
            code = (
                await session.execute(select(Lab.code).where(Lab.id == user.lab_id))
            ).scalar_one_or_none()
        if code:
            channels.append(f"dashboard:events:{code}")

    async def event_gen():
        async for ev in listen(channels):
            yield {"event": "dashboard", "data": ev}

    return EventSourceResponse(event_gen())

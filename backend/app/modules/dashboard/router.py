"""Dashboard HTTP routes.

* ``GET /api/dashboard``        — one-shot snapshot. The frontend polls every
  30s via TanStack Query.
* ``GET /api/dashboard/stream`` — SSE channel. Yields event-name lines (no
  payload) so the FE invalidates the ``["dashboard"]`` query and re-fetches
  the full snapshot.

The endpoint is gated by ``dashboard:read``; the seeded ``general_supervisor``,
``lab_supervisor``, and ``system_admin`` roles all hold it. ``lab_engineer``
does NOT have ``dashboard:read``, so per-lab subscription only needs to be
arranged for ``lab_supervisor``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from app.common.dependencies import CurrentUser, get_current_user, require_permission
from app.common.schemas import ApiResponse
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

    * ``dashboard:events:global`` — every caller listens here so truly
      cross-lab events (e.g. a new pending_approval order with no lab yet)
      always reach the page.
    * ``dashboard:events:{lab_code}`` — added for ``lab_supervisor`` so
      per-lab fanouts are received.

    Patterns:

    * ``dashboard:events:*`` — used by cross-lab viewers
      (``general_supervisor`` / ``system_admin``) so they pick up every
      lab's per-lab events without subscribing to each lab channel by name
      and without the publisher having to mirror per-lab events into the
      global channel (which would double-deliver to lab_supervisor).

    ``CurrentUser`` already carries ``lab_code`` (resolved in
    ``get_current_user``); no extra DB lookup is needed here. The handler
    yields event-name strings; the FE only needs the *signal*, not the
    payload, since it re-fetches the full snapshot after each one.
    """
    if user.role == "lab_supervisor" and user.lab_code is not None:
        # lab_supervisor: explicit subscribe to global + own lab. No PSUB
        # wildcard, so events on other labs are correctly filtered out.
        channels = ["dashboard:events:global", f"dashboard:events:{user.lab_code}"]
        patterns: list[str] = []
    elif "*" in user.permissions or user.role in ("system_admin", "general_supervisor"):
        # Cross-lab viewers: ``dashboard:events:*`` (PSUBSCRIBE) already
        # matches ``dashboard:events:global``, so an explicit SUBSCRIBE to
        # global would double-deliver every global event (one ``message``
        # frame + one ``pmessage`` frame).
        channels = []
        patterns = ["dashboard:events:*"]
    else:
        # Permission gate already restricts this endpoint to dashboard:read
        # roles, so we don't expect to land here. Safety fallback: only
        # global events, so unexpected roles don't get cross-lab leakage.
        channels = ["dashboard:events:global"]
        patterns = []

    async def event_gen():
        async for ev in listen(channels, patterns=patterns):
            yield {"event": "dashboard", "data": ev}

    return EventSourceResponse(event_gen())

"""Routing-layer entrypoint for ``/api/dashboard``.

Re-exports the router defined in :mod:`app.modules.dashboard.router` so the
central registry (``app.routes.registry.ALL_ROUTERS``) can pick it up via
the existing module pattern.
"""

from app.modules.dashboard.router import router

__all__ = ["router"]

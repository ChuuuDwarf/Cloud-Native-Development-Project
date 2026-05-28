"""Routing-layer entrypoint for ``/api/dashboard``.

Re-exports the router defined in :mod:`app.modules.dashboard.router` so the
central registry (``app.routes.registry.ALL_ROUTERS``) can pick it up via
the existing module pattern.

The old service-based implementation lives in
``app/services/dashboard.py`` + ``app/schemas/dashboard.py`` and is no longer
mounted on the app; those files are kept for now and will be removed in a
follow-up cleanup commit once the FE has cut over.
"""

from app.modules.dashboard.router import router

__all__ = ["router"]

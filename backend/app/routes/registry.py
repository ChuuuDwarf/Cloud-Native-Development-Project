"""Central route registry.

All API controllers are mounted from app/routes.
"""

from fastapi import APIRouter

from app.routes.auth import router as auth_router
from app.routes.labs import router as labs_router
from app.routes.master_data import router as master_data_router
from app.routes.orders import router as orders_router
from app.routes.quotas import router as quotas_router
from app.routes.roles import router as roles_router
from app.routes.samples import router as samples_router
from app.routes.users import router as users_router
from app.routes.transfers import router as transfers_router
from app.routes.wips import router as wips_router
from app.routes.workflow_views import router as workflow_views_router

ALL_ROUTERS: list[APIRouter] = [
    auth_router,
    users_router,
    roles_router,
    master_data_router,
    labs_router,
    orders_router,
    samples_router,
    quotas_router,
    transfers_router,
    wips_router,
    workflow_views_router,
]

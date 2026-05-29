"""Central route registry.

All API controllers are mounted from app/routes.
"""

from fastapi import APIRouter

from app.routes.auth import router as auth_router
from app.routes.closures import router as closures_router
from app.routes.dashboard import router as dashboard_router
from app.routes.dispatches import router as dispatches_router
from app.routes.experiment_runs import router as experiment_runs_router
from app.routes.issues import router as issues_router
from app.routes.labs import router as labs_router
from app.routes.machines import router as machines_router
from app.routes.master_data import router as master_data_router
from app.routes.notifications import router as notifications_router
from app.routes.orders import router as orders_router
from app.routes.others import router as others_router
from app.routes.quotas import router as quotas_router
from app.routes.recipes import router as recipes_router
from app.routes.reports import router as reports_router
from app.routes.roles import router as roles_router
from app.routes.samples import router as samples_router
from app.routes.transfers import router as transfers_router
from app.routes.users import router as users_router
from app.routes.wips import router as wips_router
from app.routes.workflow_views import router as workflow_views_router

ALL_ROUTERS: list[APIRouter] = [
    auth_router,
    dashboard_router,
    issues_router,
    users_router,
    roles_router,
    master_data_router,
    labs_router,
    notifications_router,
    orders_router,
    samples_router,
    quotas_router,
    transfers_router,
    wips_router,
    # 組員 C（機台/recipe/派工）與 D（實驗執行/報告/結案）
    machines_router,
    recipes_router,
    dispatches_router,
    experiment_runs_router,
    reports_router,
    closures_router,
    others_router,
    workflow_views_router,
]

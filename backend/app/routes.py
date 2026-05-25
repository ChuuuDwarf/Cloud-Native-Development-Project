"""Central route registry — every module router is mounted here, in one place.

When you add a new module:
1. Create ``app/modules/<name>/router.py`` exporting ``router``
2. Import it below
3. Append to ``ALL_ROUTERS``
"""

from fastapi import APIRouter

from app.modules.audit_logs.router import router as audit_logs_router
from app.modules.auth.router import router as auth_router
from app.modules.closures.router import router as closures_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.departments.router import router as departments_router
from app.modules.dispatches.router import router as dispatches_router
from app.modules.experiment_runs.router import router as experiment_runs_router
from app.modules.files.router import router as files_router
from app.modules.issues.router import router as issues_router
from app.modules.labs.router import router as labs_router
from app.modules.machines.router import router as machines_router
from app.modules.master_data.router import router as master_data_router
from app.modules.notifications.router import router as notifications_router
from app.modules.orders.router import router as orders_router
from app.modules.recipes.router import router as recipes_router
from app.modules.reports.router import router as reports_router
from app.modules.roles.router import router as roles_router
from app.modules.samples.router import router as samples_router
from app.modules.schedules.router import router as schedules_router
from app.modules.storage_locations.router import router as storage_locations_router
from app.modules.system_settings.router import router as system_settings_router
from app.modules.users.router import router as users_router
from app.modules.wips.router import router as wips_router

ALL_ROUTERS: list[APIRouter] = [
    auth_router,
    users_router,
    roles_router,
    master_data_router,
    system_settings_router,
    labs_router,
    departments_router,
    storage_locations_router,
    files_router,
    audit_logs_router,
    issues_router,
    notifications_router,
    dashboard_router,
    orders_router,
    samples_router,
    wips_router,
    machines_router,
    recipes_router,
    schedules_router,
    dispatches_router,
    experiment_runs_router,
    reports_router,
    closures_router,
]

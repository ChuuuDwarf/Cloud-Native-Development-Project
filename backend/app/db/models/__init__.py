"""All ORM models — importing this triggers SQLAlchemy registration.

Alembic ``env.py`` and seed scripts import * from here to ensure every model
is attached to ``Base.metadata`` before introspection.

When teammates add their own models (orders, samples, wips, machines, recipes,
schedules, dispatches, experiment_runs, reports), they should:
1. Add the file under ``app/db/models/<name>.py``
2. Append the import below
3. Run ``alembic revision --autogenerate -m "add <table>"``
"""

from app.db.models.audit_logs import AuditLog
from app.db.models.departments import Department
from app.db.models.files import File
from app.db.models.issues import Issue
from app.db.models.labs import Lab, LabCapability
from app.db.models.notifications import Notification, NotificationDelivery
from app.db.models.roles import Permission, Role, role_permissions, user_roles
from app.db.models.storage_locations import StorageLocation
from app.db.models.system_settings import SystemSetting, SystemSettingHistory
from app.db.models.users import User

from app.db.models.order_management import (
    OrderHistoryModel,
    OrderItemModel,
    OrderModel,
    QuotaSettingModel,
    QuotaUsageModel,
)

__all__ = [
    "OrderModel",
    "OrderItemModel",
    "OrderHistoryModel",
    "QuotaSettingModel",
    "QuotaUsageModel",
    "AuditLog",
    "Department",
    "File",
    "Issue",
    "Lab",
    "LabCapability",
    "Notification",
    "NotificationDelivery",
    "Permission",
    "Role",
    "StorageLocation",
    "SystemSetting",
    "SystemSettingHistory",
    "User",
    "role_permissions",
    "user_roles",
]

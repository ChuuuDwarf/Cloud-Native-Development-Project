"""Shared enums consumed by both backend modules and (via sync_enums.py) the frontend.

When adding a new enum:
1. Create ``<name>.py`` in this directory with a ``str, Enum`` class
2. Re-export it here so ``from app.common.enums import ...`` works
3. Add a Chinese display label in ``frontend/src/constants/status-labels.ts``
4. Run ``python scripts/sync_enums.py`` to refresh ``frontend/src/constants/enums.ts``
"""

from app.common.enums.audit_target_type import AuditTargetType
from app.common.enums.issue_action import IssueAction
from app.common.enums.issue_status import IssueStatus
from app.common.enums.issue_type import IssueType
from app.common.enums.machine_status import MachineStatus
from app.common.enums.notification_channel import NotificationChannel
from app.common.enums.notification_status import NotificationStatus
from app.common.enums.order_action import OrderAction
from app.common.enums.order_status import OrderStatus
from app.common.enums.report_action import ReportAction
from app.common.enums.report_status import ReportStatus
from app.common.enums.severity import Severity
from app.common.enums.storage_status import StorageStatus
from app.common.enums.user_status import UserStatus
from app.common.enums.wip_action import WipAction
from app.common.enums.wip_status import WipStatus

__all__ = [
    "AuditTargetType",
    "IssueAction",
    "IssueStatus",
    "IssueType",
    "MachineStatus",
    "NotificationChannel",
    "NotificationStatus",
    "OrderAction",
    "OrderStatus",
    "ReportAction",
    "ReportStatus",
    "Severity",
    "StorageStatus",
    "UserStatus",
    "WipAction",
    "WipStatus",
]

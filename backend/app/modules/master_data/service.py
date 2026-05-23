"""MasterDataService — aggregates everything a frontend dropdown might need."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.enums import (
    IssueStatus,
    IssueType,
    MachineStatus,
    NotificationStatus,
    OrderStatus,
    ReportStatus,
    Severity,
    UserStatus,
    WipStatus,
)
from app.db.models import Department, Lab, LabCapability, Permission, Role, StorageLocation


class MasterDataService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def gather(self) -> dict[str, Any]:
        roles = (
            (
                await self._session.execute(
                    select(Role).options(selectinload(Role.permissions)).order_by(Role.name)
                )
            )
            .scalars()
            .all()
        )
        permissions = (
            (await self._session.execute(select(Permission).order_by(Permission.code)))
            .scalars()
            .all()
        )
        labs = (
            (
                await self._session.execute(
                    select(Lab).where(Lab.is_active.is_(True)).order_by(Lab.code)
                )
            )
            .scalars()
            .all()
        )
        departments = (
            (
                await self._session.execute(
                    select(Department)
                    .where(Department.is_active.is_(True))
                    .order_by(Department.code)
                )
            )
            .scalars()
            .all()
        )
        storage = (
            (
                await self._session.execute(
                    select(StorageLocation)
                    .where(StorageLocation.is_active.is_(True))
                    .order_by(StorageLocation.code)
                )
            )
            .scalars()
            .all()
        )
        capabilities = (
            (
                await self._session.execute(
                    select(LabCapability.experiment_item)
                    .join(Lab)
                    .where(Lab.is_active.is_(True))
                    .distinct()
                    .order_by(LabCapability.experiment_item)
                )
            )
            .scalars()
            .all()
        )
        experiments = (
            (
                await self._session.execute(
                    select(LabCapability)
                    .join(Lab)
                    .where(Lab.is_active.is_(True))
                    .order_by(Lab.code, LabCapability.experiment_item)
                )
            )
            .scalars()
            .all()
        )

        return {
            "roles": [
                {
                    "id": str(r.id),
                    "name": r.name,
                    "description": r.description,
                    "permissions": [p.code for p in r.permissions],
                }
                for r in roles
            ],
            "permissions": [
                {"id": str(p.id), "code": p.code, "description": p.description} for p in permissions
            ],
            "labs": [
                {"id": str(lab.id), "code": lab.code, "name": lab.name, "capacity": lab.capacity}
                for lab in labs
            ],
            "departments": [{"id": str(d.id), "code": d.code, "name": d.name} for d in departments],
            "experiments": [
                {
                    "id": str(capability.id),
                    "name": capability.experiment_item,
                    "labId": str(capability.lab_id),
                }
                for capability in experiments
            ],
            "storageLocations": [
                {"id": str(s.id), "code": s.code, "name": s.name, "description": s.description}
                for s in storage
            ],
            "experimentItems": list(capabilities),
            # Static enums — never DB-bound, but exposed here so the frontend has one source
            "orderStatuses": [s.value for s in OrderStatus],
            "wipStatuses": [s.value for s in WipStatus],
            "machineStatuses": [s.value for s in MachineStatus],
            "reportStatuses": [s.value for s in ReportStatus],
            "issueStatuses": [s.value for s in IssueStatus],
            "issueTypes": [t.value for t in IssueType],
            "notificationStatuses": [s.value for s in NotificationStatus],
            "userStatuses": [s.value for s in UserStatus],
            "severities": [s.value for s in Severity],
        }

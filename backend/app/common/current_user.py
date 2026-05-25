"""Shared current-user projection helpers for route/service layers."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import CurrentUser
from app.db.models.departments import Department
from app.db.models.labs import Lab

ROLE_LABELS = {
    "system_admin": "系統管理者",
    "lab_supervisor": "實驗室主管",
    "lab_engineer": "實驗室人員",
    "plant_user": "廠區使用者",
}


async def build_current_user(
    current_user: CurrentUser,
    db: AsyncSession,
) -> dict:
    """Build the API-facing current user dict used by sample/WIP/transfer flows."""

    lab_name = None
    department_name = None

    if current_user.lab_id:
        lab = await db.scalar(select(Lab).where(Lab.id == current_user.lab_id))
        if lab:
            lab_name = lab.name

    if current_user.department_id:
        department = await db.scalar(
            select(Department).where(Department.id == current_user.department_id)
        )
        if department:
            department_name = department.name

    return {
        "id": str(current_user.id),
        "name": current_user.name,
        "role": current_user.role,
        "role_name": ROLE_LABELS.get(current_user.role, current_user.role),
        "department": department_name or lab_name or "",
        "lab_name": lab_name,
        "email": current_user.email,
    }

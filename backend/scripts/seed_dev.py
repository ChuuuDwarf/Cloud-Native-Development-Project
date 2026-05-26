"""Idempotent dev seed: 4 roles + permission set + 4 sample users + labs + departments.

Run from ``backend/`` (after ``alembic upgrade head``)::

    python scripts/seed_dev.py

Re-runs safely: every row is upserted by natural key (email / code / name).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import selectinload

BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.common.enums import UserStatus  # noqa: E402
from app.core.database import AsyncSessionLocal  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.models import (  # noqa: E402
    Department,
    Lab,
    LabCapability,
    Permission,
    QuotaSettingModel,
    Role,
    StorageLocation,
    User,
)

# ---------------------------------------------------------------------------
# Permission catalog — keep in sync with router require_permission(...) usage.
# ---------------------------------------------------------------------------

PERMISSIONS: list[tuple[str, str]] = [
    # users / accounts
    ("users:read", "查看使用者列表與單筆"),
    ("users:create", "建立新使用者"),
    ("users:update", "修改使用者資料、角色、狀態、密碼"),
    # orders
    ("orders:read", "查看委託單"),
    ("orders:create", "建立委託單"),
    ("orders:approve", "核准 / 退回 / 拒絕委託單"),
    ("orders:close", "結案"),
    # samples / wips
    ("samples:read", "查看樣品"),
    ("samples:create", "建立收樣"),
    ("wips:read", "查看 WIP"),
    ("wips:create", "建立 WIP / 分貨"),
    ("wips:dispatch", "派工"),
    # machines / recipes / schedules / dispatches
    ("machines:read", "查看機台"),
    ("machines:manage", "管理機台 (CRUD)"),
    ("recipes:read", "查看 Recipe"),
    ("recipes:manage", "管理 Recipe"),
    ("schedules:read", "查看排程"),
    ("schedules:manage", "編輯排程"),
    ("dispatches:read", "查看派工"),
    ("dispatches:manage", "建立 / 修改派工"),
    # experiment runs / reports / closures (組員 C/D router require_permission codes)
    ("experiment_runs:read", "查看實驗執行"),
    ("experiment_runs:execute", "上下機、回報結果"),
    ("experiments:operate", "上下機、進度、結果上傳、確認、提出中止申請"),
    ("experiments:review", "主管審核中止申請"),
    ("reports:read", "查看報告"),
    ("reports:create", "建立報告草稿"),
    ("reports:publish", "發布報告"),
    ("reports:operate", "建立 / 編輯 / 送審 / 發布報告"),
    ("reports:review", "主管審核報告"),
    ("closures:operate", "結案、入庫 / 出庫取件"),
    # issues / notifications
    ("issues:read", "查看異常 / 告警"),
    ("issues:create", "建立異常"),
    ("issues:update", "編輯異常欄位 (title / 指派 / severity)"),
    ("issues:close", "關閉告警"),
    ("issues:escalate", "升級告警"),
    ("notifications:read", "查看通知"),
    # dashboard / audit
    ("dashboard:read", "查看主管儀表板"),
    ("audit_logs:read", "查看稽核紀錄"),
    # system / config
    ("system_settings:read", "查看系統設定"),
    ("system_settings:update", "修改系統設定"),
    ("labs:read", "查看實驗室"),
    ("labs:manage", "管理實驗室"),
    ("departments:read", "查看部門"),
    ("departments:manage", "管理部門"),
    ("storage_locations:read", "查看倉位"),
    ("storage_locations:manage", "管理倉位"),
]

# ---------------------------------------------------------------------------
# Role -> permission code list. Use "*" wildcard for sysadmin.
# ---------------------------------------------------------------------------

# Engineer is the base "operator" role. Supervisor inherits everything
# engineer can do PLUS commercial-approval authority (orders, recipes,
# schedules, audit-logs visibility, dashboard). Defined as a superset so we
# never drift — bumping engineer perms auto-bumps supervisor.
#
# Note on `machines:manage`, `reports:publish`, `issues:close`,
# `issues:escalate`: these all sit on engineer (not supervisor-only) by
# design. The warning-escalation flow goes engineer-first: a machine
# anomaly notifies the on-shift engineer; if they don't close the issue
# within the configured window the system auto-escalates to supervisor.
# So engineer needs to be able to close + escalate issues themselves (the
# first-responder), publish their own reports, and toggle machines in/out
# of maintenance status. Recipes + schedules stay supervisor-only (process
# IP + planning authority).
LAB_ENGINEER_PERMS: list[str] = [
    "orders:read",
    "samples:read",
    "samples:create",
    "wips:read",
    "wips:create",
    "wips:dispatch",
    "machines:read",
    "machines:manage",
    "recipes:read",
    "schedules:read",
    "dispatches:read",
    "dispatches:manage",
    "experiment_runs:read",
    "experiment_runs:execute",
    "experiments:operate",
    "reports:read",
    "reports:create",
    "reports:publish",
    "reports:operate",
    "closures:operate",
    "issues:read",
    "issues:create",
    "issues:update",
    "issues:close",
    "issues:escalate",
    "notifications:read",
    "labs:read",
    "storage_locations:read",
]

LAB_SUPERVISOR_EXTRA_PERMS: list[str] = [
    "users:read",
    "orders:approve",
    "orders:close",
    "recipes:manage",
    "schedules:manage",
    "dashboard:read",
    "audit_logs:read",
    "departments:read",
    # 主管專屬審核權（中止申請、報告審核）
    "experiments:review",
    "reports:review",
]

ROLES: dict[str, tuple[str, list[str]]] = {
    "system_admin": (
        "系統管理者 (Sysadmin)",
        ["*"],
    ),
    "lab_supervisor": (
        "實驗室主管",
        # Superset: engineer perms + supervisor-only extras.
        sorted(set(LAB_ENGINEER_PERMS + LAB_SUPERVISOR_EXTRA_PERMS)),
    ),
    "lab_engineer": (
        "實驗室人員",
        LAB_ENGINEER_PERMS,
    ),
    "plant_user": (
        "廠區使用者",
        [
            "orders:read",
            "orders:create",
            "samples:read",
            "notifications:read",
            "labs:read",
            "departments:read",
        ],
    ),
}

# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

DEPARTMENTS: list[tuple[str, str]] = [
    ("DEPT-RD", "研發部"),
    ("DEPT-MFG", "製造部"),
    ("DEPT-QA", "品保部"),
]

LABS: list[tuple[str, str, int, list[str]]] = [
    ("LAB-A", "材料分析實驗室", 12, ["SEM", "FIB", "EDX"]),
    ("LAB-B", "電性測試實驗室", 10, ["IV", "CV", "Probe"]),
    ("LAB-C", "可靠度實驗室", 8, ["TC", "HTOL", "ESD"]),
]

STORAGE_LOCATIONS: list[tuple[str, str, str]] = [
    ("STG-A1", "A 區待測架", "材料分析待測樣品"),
    ("STG-A2", "A 區完成架", "材料分析完成樣品"),
    ("STG-B1", "B 區待測架", "電性測試待測樣品"),
]

# email, name, role-name, department-code, lab-code, password
USERS: list[tuple[str, str, str, str | None, str | None, str]] = [
    ("admin@example.com", "Sys Admin", "system_admin", None, None, "Admin1234"),
    ("supervisor@example.com", "譚曉蓉", "lab_supervisor", None, "LAB-A", "Super1234"),
    ("supervisor2@example.com", "王小明", "lab_supervisor", None, "LAB-B", "Super1234"),
    ("supervisor3@example.com", "陳美秀", "lab_supervisor", None, "LAB-C", "Super1234"),
    ("engineer@example.com", "李大明", "lab_engineer", None, "LAB-A", "Engin1234"),
    ("engineer2@example.com", "林妏媞", "lab_engineer", None, "LAB-B", "Engin1234"),
    ("engineer3@example.com", "周秉倫", "lab_engineer", None, "LAB-C", "Engin1234"),
    ("requester@example.com", "楚顏璧", "plant_user", "DEPT-RD", None, "Reque1234"),
    ("requester2@example.com", "林小美", "plant_user", "DEPT-MFG", None, "Reque1234"),
]

DEFAULT_USER_QUOTAS: list[tuple[str, int]] = [
    ("requester@example.com", 10),
    ("requester2@example.com", 10),
]

DEFAULT_DEPARTMENT_QUOTAS: list[tuple[str, int]] = [
    ("DEPT-RD", 50),
    ("DEPT-MFG", 30),
    ("DEPT-QA", 20),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def upsert_permission(session, code: str, description: str) -> Permission:
    existing = (
        await session.execute(select(Permission).where(Permission.code == code))
    ).scalar_one_or_none()
    if existing:
        if existing.description != description:
            existing.description = description
        return existing
    perm = Permission(code=code, description=description)
    session.add(perm)
    await session.flush()
    return perm


async def upsert_role(
    session,
    name: str,
    description: str,
    permission_codes: list[str],
    perm_lookup: dict[str, Permission],
) -> Role:
    """Two paths, both kept lazy-load-free:

    - New role: assign ``permissions`` BEFORE ``session.add`` (transient object,
      no DB roundtrip on relationship set).
    - Existing role: load WITH ``selectinload(Role.permissions)`` so the
      relationship is already in memory before reassignment.
    """
    desired = [perm_lookup[c] for c in permission_codes if c in perm_lookup]

    role = (
        await session.execute(
            select(Role).options(selectinload(Role.permissions)).where(Role.name == name)
        )
    ).scalar_one_or_none()

    if role is None:
        role = Role(name=name, description=description)
        role.permissions = desired
        session.add(role)
        await session.flush()
    else:
        role.description = description
        role.permissions = desired

    return role


async def upsert_department(session, code: str, name: str) -> Department:
    existing = (
        await session.execute(select(Department).where(Department.code == code))
    ).scalar_one_or_none()
    if existing:
        existing.name = name
        return existing
    dept = Department(code=code, name=name, is_active=True)
    session.add(dept)
    await session.flush()
    return dept


async def upsert_lab(session, code: str, name: str, capacity: int, capabilities: list[str]) -> Lab:
    lab = (await session.execute(select(Lab).where(Lab.code == code))).scalar_one_or_none()
    if not lab:
        lab = Lab(code=code, name=name, capacity=capacity, is_active=True)
        session.add(lab)
        await session.flush()
    else:
        lab.name = name
        lab.capacity = capacity

    # Refresh capabilities deterministically.
    existing_caps = (
        (await session.execute(select(LabCapability).where(LabCapability.lab_id == lab.id)))
        .scalars()
        .all()
    )
    existing_items = {c.experiment_item for c in existing_caps}
    for item in capabilities:
        if item not in existing_items:
            session.add(LabCapability(lab_id=lab.id, experiment_item=item))
    return lab


async def upsert_storage(session, code: str, name: str, description: str) -> StorageLocation:
    existing = (
        await session.execute(select(StorageLocation).where(StorageLocation.code == code))
    ).scalar_one_or_none()
    if existing:
        existing.name = name
        existing.description = description
        return existing
    sl = StorageLocation(code=code, name=name, description=description, is_active=True)
    session.add(sl)
    await session.flush()
    return sl


async def upsert_quota_setting(
    session,
    scope_type: str,
    scope_id: str,
    monthly_limit: int,
    urgent_limit: int | None = None,
    critical_limit: int | None = None,
) -> QuotaSettingModel:
    """Upsert quota by natural key: (scope_type, scope_id).

    If old duplicate rows already exist from previous tests, keep the newest
    row and delete the older rows so the quota page does not show duplicates.
    """
    existing_rows = (
        (
            await session.execute(
                select(QuotaSettingModel)
                .where(
                    QuotaSettingModel.scope_type == scope_type,
                    QuotaSettingModel.scope_id == scope_id,
                )
                .order_by(QuotaSettingModel.id.desc())
            )
        )
        .scalars()
        .all()
    )

    if existing_rows:
        quota = existing_rows[0]
        quota.monthly_limit = monthly_limit
        quota.urgent_limit = urgent_limit
        quota.critical_limit = critical_limit
        quota.is_active = True

        # Remove duplicate quota settings for the same scope.
        for duplicate in existing_rows[1:]:
            await session.delete(duplicate)

        await session.flush()
        return quota

    quota = QuotaSettingModel(
        scope_type=scope_type,
        scope_id=scope_id,
        monthly_limit=monthly_limit,
        urgent_limit=urgent_limit,
        critical_limit=critical_limit,
        is_active=True,
    )
    session.add(quota)
    await session.flush()
    return quota


async def upsert_user(
    session,
    email: str,
    name: str,
    role: Role,
    department: Department | None,
    lab: Lab | None,
    plaintext_password: str,
) -> User:
    """Same lazy-load-avoidance pattern as upsert_role:
    new -> assign relationship before add; existing -> selectinload first.
    """
    desired_roles = [role]

    user = (
        await session.execute(
            select(User).options(selectinload(User.roles)).where(User.email == email)
        )
    ).scalar_one_or_none()

    if user is None:
        user = User(
            email=email,
            name=name,
            password_hash=hash_password(plaintext_password),
            department_id=department.id if department else None,
            lab_id=lab.id if lab else None,
            status=UserStatus.ACTIVE,
            is_active=True,
        )
        user.roles = desired_roles
        session.add(user)
        await session.flush()
    else:
        user.name = name
        user.password_hash = hash_password(plaintext_password)
        user.department_id = department.id if department else None
        user.lab_id = lab.id if lab else None
        user.status = UserStatus.ACTIVE
        user.is_active = True
        user.roles = desired_roles

    return user


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> None:
    async with AsyncSessionLocal() as session:
        # Permissions
        perm_map: dict[str, Permission] = {}
        for code, desc in PERMISSIONS:
            perm_map[code] = await upsert_permission(session, code, desc)

        # Provide a "*" wildcard permission row too, so role.permissions queries
        # don't have to special-case it. The dependency checks the string directly.
        if "*" not in perm_map:
            perm_map["*"] = await upsert_permission(session, "*", "Wildcard — all permissions")

        # Roles
        role_map: dict[str, Role] = {}
        for key, (desc, codes) in ROLES.items():
            role_map[key] = await upsert_role(session, key, desc, codes, perm_map)

        # Departments
        dept_map: dict[str, Department] = {}
        for code, name in DEPARTMENTS:
            dept_map[code] = await upsert_department(session, code, name)

        # Labs
        lab_map: dict[str, Lab] = {}
        for code, name, capacity, caps in LABS:
            lab_map[code] = await upsert_lab(session, code, name, capacity, caps)

        # Storage
        for code, name, desc in STORAGE_LOCATIONS:
            await upsert_storage(session, code, name, desc)

        # Users
        user_map: dict[str, User] = {}
        for email, name, role_key, dept_code, lab_code, password in USERS:
            user_map[email] = await upsert_user(
                session,
                email=email,
                name=name,
                role=role_map[role_key],
                department=dept_map.get(dept_code) if dept_code else None,
                lab=lab_map.get(lab_code) if lab_code else None,
                plaintext_password=password,
            )

        # Quota settings
        # Use real DB UUIDs, not legacy fake ids such as user001 / D001.
        for email, monthly_limit in DEFAULT_USER_QUOTAS:
            user = user_map.get(email)
            if user is None:
                user = (
                    await session.execute(select(User).where(User.email == email))
                ).scalar_one_or_none()

            if user is None:
                sys.stdout.write(f"Skip user quota: user not found: {email}\n")
                continue

            await upsert_quota_setting(
                session,
                scope_type="user",
                scope_id=str(user.id),
                monthly_limit=monthly_limit,
            )

        for department_code, monthly_limit in DEFAULT_DEPARTMENT_QUOTAS:
            department = dept_map.get(department_code)
            if department is None:
                department = (
                    await session.execute(
                        select(Department).where(Department.code == department_code)
                    )
                ).scalar_one_or_none()

            if department is None:
                message = f"Skip department quota: department not found: {department_code}\n"
                sys.stdout.write(message)
                continue

            await upsert_quota_setting(
                session,
                scope_type="department",
                scope_id=str(department.id),
                monthly_limit=monthly_limit,
            )

        await session.commit()

    sys.stdout.write(
        "Seed complete.\n"
        "  admin@example.com      / Admin1234   (system_admin)\n"
        "  supervisor@example.com / Super1234   (lab_supervisor)\n"
        "  supervisor2@example.com / Super1234   (lab_supervisor)\n"
        "  supervisor3@example.com / Super1234   (lab_supervisor)\n"
        "  engineer@example.com   / Engin1234   (lab_engineer)\n"
        "  engineer2@example.com  / Engin1234   (lab_engineer)\n"
        "  engineer3@example.com  / Engin1234   (lab_engineer)\n"
        "  requester@example.com  / Reque1234   (plant_user)\n"
        "  requester2@example.com / Reque1234   (plant_user)\n"
        "Quota defaults:\n"
        "  requester@example.com  monthly_limit=10\n"
        "  DEPT-RD                monthly_limit=50\n"
        "  DEPT-MFG               monthly_limit=30\n"
        "  DEPT-QA                monthly_limit=20\n"
    )


if __name__ == "__main__":
    asyncio.run(main())

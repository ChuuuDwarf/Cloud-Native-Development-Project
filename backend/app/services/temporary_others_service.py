# TODO(integration): 這個 route 是暫時替代層，專案合併後預期會刪除。
# 目前提供 role/order/system_setting/schedule/warn 等模組尚未完成時的 mock API。
# 後續請依 sample_management.md 改接：
# - role.md: GET /api/me
# - order_management.md: GET /api/orders/:id, POST /api/orders/:id/actions
# - system_setting.md: GET /api/storage-locations, GET /api/labs, GET /api/master-data
# - schedule.md: GET /api/schedules, GET /api/dispatches
# - warn.md: GET /api/issues, POST /api/issues
"""Temporary Others helper/service layer.

這個檔案由原本過長的 route 檔拆出，集中放置權限判斷、位置轉換、ID 產生、資料查詢等輔助邏輯。
Route 檔應只保留 HTTP endpoint，避免 API 入口與流程邏輯混在一起。
"""

import json

from fastapi import HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

mock_users = [
    {
        "id": "user-factory-001",
        "name": "王建國",
        "role": "factory_user",
        "role_name": "廠區使用者",
        "department": "F12 廠",
        "lab_name": None,
        "email": "factory.user@example.com",
    },
    {
        "id": "user-laba-001",
        "name": "張志明",
        "role": "lab_staff",
        "role_name": "實驗室 A 人員",
        "department": "Lab A",
        "lab_name": "Lab A",
        "email": "lab.a@example.com",
    },
    {
        "id": "user-labb-001",
        "name": "林雅婷",
        "role": "lab_staff",
        "role_name": "實驗室 B 人員",
        "department": "Lab B",
        "lab_name": "Lab B",
        "email": "lab.b@example.com",
    },
    {
        "id": "user-labc-001",
        "name": "吳柏翰",
        "role": "lab_staff",
        "role_name": "實驗室 C 人員",
        "department": "Lab C",
        "lab_name": "Lab C",
        "email": "lab.c@example.com",
    },
    {
        "id": "user-supervisor-001",
        "name": "陳主管",
        "role": "lab_supervisor",
        "role_name": "實驗室主管",
        "department": "Lab 管理部",
        "lab_name": "Lab A",
        "email": "supervisor@example.com",
    },
    {
        "id": "user-admin-001",
        "name": "系統管理者",
        "role": "system_admin",
        "role_name": "系統管理者",
        "department": "IT",
        "lab_name": None,
        "email": "admin@example.com",
    },
]

# 保留全域 fallback。
# 有 x-user-id header 時優先使用 header。
# 沒有 header 時，使用這個全域目前使用者。
current_user_id = "user-laba-001"

mock_labs = [
    {"id": "lab-a", "name": "Lab A", "description": "材料與電性測試"},
    {"id": "lab-b", "name": "Lab B", "description": "光學與可靠度測試"},
    {"id": "lab-c", "name": "Lab C", "description": "化學分析"},
]

mock_storage_locations = [
    {
        "id": "storage-a-01",
        "code": "A-R01-S01",
        "name": "Lab A 待取件架 1",
        "lab_name": "Lab A",
    },
    {
        "id": "storage-a-02",
        "code": "A-R01-S02",
        "name": "Lab A 暫存架 2",
        "lab_name": "Lab A",
    },
    {
        "id": "storage-b-01",
        "code": "B-R01-S01",
        "name": "Lab B 待取件架 1",
        "lab_name": "Lab B",
    },
]

mock_orders = [
    {
        "id": "order-001",
        "order_no": "ORD-2026-0001",
        "applicant_name": "王建國",
        "applicant_department": "F12 廠",
        "sample_name": "晶圓切片 A",
        "sample_quantity": "2",
        "requested_experiments": [
            {"lab_name": "Lab A", "experiment_item": "SEM 觀察"},
            {"lab_name": "Lab B", "experiment_item": "光學量測"},
        ],
        "priority": "normal",
        "status": "sample_received",
    },
    {
        "id": "order-002",
        "order_no": "ORD-2026-0002",
        "applicant_name": "李美珍",
        "applicant_department": "F6 廠",
        "sample_name": "封裝樣品 B",
        "sample_quantity": "3",
        "requested_experiments": [
            {"lab_name": "Lab A", "experiment_item": "電性量測"},
            {"lab_name": "Lab C", "experiment_item": "化學分析"},
        ],
        "priority": "high",
        "status": "testing",
    },
]

mock_schedules = [
    {
        "id": "schedule-001",
        "wip_no": "WIP-2026-0001-A",
        "machine_name": "SEM-001",
        "status": "scheduled",
        "start_time": "2026-05-22T10:00:00",
    },
    {
        "id": "schedule-002",
        "wip_no": "WIP-2026-0001-B",
        "machine_name": "OPT-002",
        "status": "waiting_schedule",
        "start_time": None,
    },
]

mock_dispatches = [
    {
        "id": "dispatch-001",
        "wip_no": "WIP-2026-0001-A",
        "assignee_name": "張志明",
        "status": "assigned",
    }
]

mock_issues = [
    {
        "id": "issue-001",
        "type": "warning",
        "target_type": "sample",
        "target_no": "SMP-2026-0001",
        "level": "medium",
        "message": "樣品待取件超過 2 天",
        "status": "open",
    }
]

master_data = {
    "sample_statuses": [
        {"value": "pending_receive", "label": "待收樣"},
        {"value": "received", "label": "已收樣"},
        {"value": "split", "label": "已分貨"},
        {"value": "transferring", "label": "交接中"},
        {"value": "in_storage", "label": "已入庫"},
        {"value": "outbound", "label": "待取件"},
        {"value": "picked_up", "label": "已取件"},
    ],
    "wip_statuses": [
        {"value": "created", "label": "已建立"},
        {"value": "waiting_schedule", "label": "待排程"},
        {"value": "scheduled", "label": "已排程"},
        {"value": "dispatched", "label": "已派工"},
        {"value": "running", "label": "執行中"},
        {"value": "paused", "label": "暫停"},
        {"value": "completed", "label": "已完成"},
        {"value": "terminated", "label": "已終止"},
        {"value": "cancelled", "label": "已取消"},
    ],
    "priorities": [
        {"value": "low", "label": "低"},
        {"value": "normal", "label": "一般"},
        {"value": "high", "label": "高"},
        {"value": "urgent", "label": "特急"},
    ],
    "experiment_items": [
        {"value": "SEM 觀察", "label": "SEM 觀察"},
        {"value": "電性量測", "label": "電性量測"},
        {"value": "材料分析", "label": "材料分析"},
        {"value": "光學量測", "label": "光學量測"},
        {"value": "可靠度測試", "label": "可靠度測試"},
        {"value": "外觀檢查", "label": "外觀檢查"},
        {"value": "化學分析", "label": "化學分析"},
        {"value": "成分分析", "label": "成分分析"},
        {"value": "污染分析", "label": "污染分析"},
    ],
    "lab_experiment_matrix": [
        {
            "lab_name": "Lab A",
            "items": ["SEM 觀察", "電性量測", "材料分析"],
        },
        {
            "lab_name": "Lab B",
            "items": ["光學量測", "可靠度測試", "外觀檢查"],
        },
        {
            "lab_name": "Lab C",
            "items": ["化學分析", "成分分析", "污染分析"],
        },
    ],
}


def find_user(user_id: str | None):
    if not user_id:
        return None

    return next((user for user in mock_users if user["id"] == user_id), None)


def resolve_current_user(request: Request | None = None):
    user_id = None

    if request is not None:
        user_id = request.headers.get("x-user-id")

    if not user_id:
        user_id = current_user_id

    user = find_user(user_id)

    if user is None:
        raise HTTPException(status_code=404, detail="Current user not found")

    return user


def next_id(prefix: str, items: list[dict]):
    return f"{prefix}-{len(items) + 1:03d}"


def generate_order_no():
    return f"ORD-2026-{len(mock_orders) + 1:04d}"


async def generate_sample_no(db: AsyncSession):
    result = await db.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM samples
            """
        )
    )
    total = int(result.fetchone()._mapping["total"])

    for index in range(total + 1, total + 1000):
        sample_no = f"SMP-2026-{index:04d}"

        exists_result = await db.execute(
            text(
                """
                SELECT 1
                FROM samples
                WHERE sample_no = :sample_no
                LIMIT 1
                """
            ),
            {"sample_no": sample_no},
        )
        exists = exists_result.fetchone()

        if exists is None:
            return sample_no

    raise HTTPException(status_code=500, detail="Unable to generate sample_no")


async def generate_unique_wip_no(db: AsyncSession, sample_no: str, index: int):
    base_no = sample_no.replace("SMP", "WIP")

    for offset in range(index, index + 1000):
        wip_no = f"{base_no}-{offset:02d}"

        exists_result = await db.execute(
            text(
                """
                SELECT 1
                FROM wips
                WHERE wip_no = :wip_no
                LIMIT 1
                """
            ),
            {"wip_no": wip_no},
        )
        exists = exists_result.fetchone()

        if exists is None:
            return wip_no

    raise HTTPException(status_code=500, detail="Unable to generate unique_wip_no")


def lab_location(lab_name: str | None, area: str):
    if not lab_name:
        return area

    lab_name = lab_name.strip()

    if lab_name.endswith(area):
        return lab_name

    return f"{lab_name} {area}"


def receive_location(lab_name: str | None):
    return lab_location(lab_name, "收樣區")


def experiment_temp_location(lab_name: str | None):
    return lab_location(lab_name, "實驗暫存區")


def parse_requested_experiments_from_sample(sample: dict):
    # note 是使用者備註，不可再拿來存或解析系統資料。
    # 實驗需求統一從 samples.experiment_item 解析。
    # 格式例如：Lab A:SEM 觀察、Lab B:光學量測
    experiment_item = sample.get("experiment_item") or ""
    result = []

    for part in experiment_item.split("、"):
        part = part.strip()

        if ":" not in part:
            continue

        lab_name, item_name = part.split(":", 1)

        if lab_name.strip() and item_name.strip():
            result.append(
                {
                    "lab_name": lab_name.strip(),
                    "experiment_item": item_name.strip(),
                }
            )

    return result

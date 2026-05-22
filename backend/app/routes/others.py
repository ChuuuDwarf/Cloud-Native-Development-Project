import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db

router = APIRouter(
    prefix="/api",
    tags=["others"],
)

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


def generate_sample_no(db: Session):
    result = db.execute(
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

        exists = db.execute(
            text(
                """
                SELECT 1
                FROM samples
                WHERE sample_no = :sample_no
                LIMIT 1
                """
            ),
            {"sample_no": sample_no},
        ).fetchone()

        if exists is None:
            return sample_no

    raise HTTPException(status_code=500, detail="Unable to generate sample_no")


def generate_unique_wip_no(db: Session, sample_no: str, index: int):
    base_no = sample_no.replace("SMP", "WIP")

    for offset in range(index, index + 1000):
        wip_no = f"{base_no}-{offset:02d}"

        exists = db.execute(
            text(
                """
                SELECT 1
                FROM wips
                WHERE wip_no = :wip_no
                LIMIT 1
                """
            ),
            {"wip_no": wip_no},
        ).fetchone()

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
    note = sample.get("note")

    if note:
        try:
            parsed = json.loads(note)
            requested_experiments = parsed.get("requested_experiments", [])

            if isinstance(requested_experiments, list):
                return [
                    item
                    for item in requested_experiments
                    if item.get("lab_name") and item.get("experiment_item")
                ]
        except Exception:
            pass

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


@router.get("/me")
def get_current_user(request: Request):
    return resolve_current_user(request)


@router.get("/others")
def get_others(request: Request, db: Session = Depends(get_db)):
    sample_result = db.execute(
        text(
            """
            SELECT
                id,
                sample_no,
                order_no,
                sample_name,
                experiment_item,
                applicant_name,
                applicant_department,
                status,
                current_location,
                note,
                created_at
            FROM samples
            ORDER BY created_at DESC
            LIMIT 100
            """
        )
    )
    samples = [dict(row._mapping) for row in sample_result]

    wip_result = db.execute(
        text(
            """
            SELECT
                w.id,
                w.wip_no,
                w.sample_id,
                w.order_no,
                w.lab_name,
                w.experiment_item,
                w.priority,
                w.status,
                w.progress,
                w.current_location,
                w.completed_at,
                w.note,
                w.created_at,
                w.updated_at,
                s.sample_no,
                s.sample_name
            FROM wips w
            LEFT JOIN samples s
                ON s.id = w.sample_id
            ORDER BY w.created_at DESC
            LIMIT 100
            """
        )
    )
    wips = [dict(row._mapping) for row in wip_result]

    return {
        "current_user": resolve_current_user(request),
        "users": mock_users,
        "labs": mock_labs,
        "storage_locations": mock_storage_locations,
        "orders": mock_orders,
        "samples": samples,
        "wips": wips,
        "schedules": mock_schedules,
        "dispatches": mock_dispatches,
        "issues": mock_issues,
        "master_data": master_data,
    }


@router.post("/others/current-user")
def switch_current_user(payload: dict):
    global current_user_id

    user_id = payload.get("user_id")

    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    user = find_user(user_id)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    current_user_id = user_id
    return user


@router.post("/others/users")
def create_mock_user(payload: dict):
    role = payload.get("role", "lab_staff")
    role_name = payload.get("role_name")

    if not role_name:
        role_name_map = {
            "factory_user": "廠區使用者",
            "lab_staff": "實驗室人員",
            "lab_supervisor": "實驗室主管",
            "system_admin": "系統管理者",
        }
        role_name = role_name_map.get(role, role)

    user = {
        "id": payload.get("id") or next_id("user", mock_users),
        "name": payload.get("name") or "未命名使用者",
        "role": role,
        "role_name": role_name,
        "department": payload.get("department") or "",
        "lab_name": payload.get("lab_name") or None,
        "email": payload.get("email") or "",
    }

    mock_users.append(user)
    return user


@router.post("/others/labs")
def create_mock_lab(payload: dict):
    lab = {
        "id": payload.get("id") or next_id("lab", mock_labs),
        "name": payload.get("name") or "未命名實驗室",
        "description": payload.get("description") or "",
    }

    mock_labs.append(lab)
    return lab


@router.post("/others/storage-locations")
def create_mock_storage_location(payload: dict):
    location = {
        "id": payload.get("id") or next_id("storage", mock_storage_locations),
        "code": payload.get("code") or f"LOC-{len(mock_storage_locations) + 1:03d}",
        "name": payload.get("name") or "未命名儲位",
        "lab_name": payload.get("lab_name") or "Lab A",
    }

    mock_storage_locations.append(location)
    return location


@router.post("/others/orders")
def create_mock_order(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
):
    current_user = resolve_current_user(request)

    order_no = payload.get("order_no") or generate_order_no()
    applicant_name = payload.get("applicant_name") or "未命名申請人"
    applicant_department = payload.get("applicant_department") or "F12 廠"
    sample_name = payload.get("sample_name") or "未命名樣品"
    sample_quantity = payload.get("sample_quantity") or "1"
    priority = payload.get("priority") or "normal"
    status = payload.get("status") or "approved"

    requested_experiments = payload.get("requested_experiments") or []

    if not requested_experiments:
        requested_experiments = [
            {
                "lab_name": payload.get("target_lab") or "Lab A",
                "experiment_item": payload.get("test_item") or "SEM 觀察",
            }
        ]

    if status not in ("approved", "pending_receive"):
        raise HTTPException(
            status_code=400,
            detail="新增測試委託單時，status 只能是 approved 或 pending_receive",
        )

    existing_order = next(
        (
            item
            for item in mock_orders
            if item.get("order_no") == order_no or item.get("id") == payload.get("id")
        ),
        None,
    )

    if existing_order is not None:
        raise HTTPException(
            status_code=409,
            detail="這個委託單號已經存在，請換一個委託單號",
        )

    existing_sample = db.execute(
        text(
            """
            SELECT id
            FROM samples
            WHERE order_no = :order_no
            LIMIT 1
            """
        ),
        {"order_no": order_no},
    ).fetchone()

    if existing_sample is not None:
        raise HTTPException(
            status_code=409,
            detail="這個委託單號已經有對應的 sample，請換一個委託單號",
        )

    order = {
        "id": payload.get("id") or next_id("order", mock_orders),
        "order_no": order_no,
        "applicant_name": applicant_name,
        "applicant_department": applicant_department,
        "sample_name": sample_name,
        "sample_quantity": sample_quantity,
        "requested_experiments": requested_experiments,
        "priority": priority,
        "status": status,
    }

    mock_orders.append(order)

    # approved = 委託單已核准，但廠區還沒有確認送樣。
    # 這時候不建立 samples，也不會出現在 Lab 收樣區。
    if status == "approved":
        return {
            "order": order,
            "sample": None,
            "message": "委託單已建立為 approved。尚未確認送樣，因此不會產生待收樣 sample。",
        }

    # pending_receive = 廠區已確認送樣，才產生 sample 給實驗室收樣。
    experiment_summary = "、".join(
        [
            f"{item.get('lab_name')}:{item.get('experiment_item')}"
            for item in requested_experiments
        ]
    )

    first_lab = requested_experiments[0].get("lab_name", "Lab A")
    sample_no = generate_sample_no(db)
    current_location = receive_location(first_lab)

    note = json.dumps(
        {
            "source": "/api/others/orders",
            "sample_quantity": sample_quantity,
            "priority": priority,
            "requested_experiments": requested_experiments,
            "delivery_status": "confirmed",
        },
        ensure_ascii=False,
    )

    sample_result = db.execute(
        text(
            """
            INSERT INTO samples (
                sample_no,
                order_no,
                sample_name,
                experiment_item,
                applicant_name,
                applicant_department,
                status,
                current_location,
                note
            )
            VALUES (
                :sample_no,
                :order_no,
                :sample_name,
                :experiment_item,
                :applicant_name,
                :applicant_department,
                'pending_receive',
                :current_location,
                :note
            )
            RETURNING *
            """
        ),
        {
            "sample_no": sample_no,
            "order_no": order_no,
            "sample_name": sample_name,
            "experiment_item": experiment_summary,
            "applicant_name": applicant_name,
            "applicant_department": applicant_department,
            "current_location": current_location,
            "note": note,
        },
    )

    sample = dict(sample_result.fetchone()._mapping)

    db.execute(
        text(
            """
            INSERT INTO sample_histories (
                sample_id,
                action,
                from_status,
                to_status,
                description,
                operator_name,
                lab_name
            )
            VALUES (
                :sample_id,
                'delivery_confirmed_create_sample',
                NULL,
                'pending_receive',
                :description,
                :operator_name,
                :lab_name
            )
            """
        ),
        {
            "sample_id": sample["id"],
            "description": (
                f"廠區確認送樣，產生待收樣樣品 {sample_no}，"
                f"位置：{current_location}"
            ),
            "operator_name": current_user["name"],
            "lab_name": first_lab,
        },
    )

    db.commit()

    return {
        "order": order,
        "sample": sample,
        "message": "委託單已確認送樣，並同步產生 /sample 可看到的待收樣資料",
    }

@router.post("/others/schedules")
def create_mock_schedule(payload: dict):
    schedule = {
        "id": payload.get("id") or next_id("schedule", mock_schedules),
        "wip_no": payload.get("wip_no") or "WIP-NEW",
        "machine_name": payload.get("machine_name") or "未指定機台",
        "status": payload.get("status") or "waiting_schedule",
        "start_time": payload.get("start_time") or None,
    }

    mock_schedules.append(schedule)
    return schedule


@router.post("/others/dispatches")
def create_mock_dispatch(payload: dict):
    dispatch = {
        "id": payload.get("id") or next_id("dispatch", mock_dispatches),
        "wip_no": payload.get("wip_no") or "WIP-NEW",
        "assignee_name": payload.get("assignee_name") or "未指定人員",
        "status": payload.get("status") or "assigned",
    }

    mock_dispatches.append(dispatch)
    return dispatch


@router.post("/others/issues")
def create_mock_issue(payload: dict):
    issue = {
        "id": payload.get("id") or next_id("issue", mock_issues),
        "type": payload.get("type", "warning"),
        "target_type": payload.get("target_type") or payload.get("targetType") or "sample",
        "target_no": payload.get("target_no") or payload.get("targetId") or "SMP-NEW",
        "level": payload.get("level", "medium"),
        "message": payload.get("message") or payload.get("reason") or "未填寫訊息",
        "status": payload.get("status") or "open",
    }

    mock_issues.append(issue)
    return issue


@router.post("/others/master-data")
def create_mock_master_data(payload: dict):
    category = payload.get("category")
    value = payload.get("value")
    label = payload.get("label")

    if not category:
        raise HTTPException(status_code=400, detail="category is required")

    if not value:
        raise HTTPException(status_code=400, detail="value is required")

    if not label:
        raise HTTPException(status_code=400, detail="label is required")

    if category not in master_data:
        master_data[category] = []

    item = {
        "value": value,
        "label": label,
    }

    master_data[category].append(item)
    return item


@router.post("/others/samples/{sample_id}/generate-wips")
def generate_missing_wips_for_sample(
    sample_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    current_user = resolve_current_user(request)

    sample_result = db.execute(
        text(
            """
            SELECT *
            FROM samples
            WHERE id = :sample_id
            """
        ),
        {"sample_id": sample_id},
    )

    sample_row = sample_result.fetchone()

    if sample_row is None:
        raise HTTPException(status_code=404, detail="Sample not found")

    sample = dict(sample_row._mapping)

    if sample["status"] not in ("received", "split"):
        raise HTTPException(
            status_code=400,
            detail="只有已收樣 received 或已分貨 split 的樣品可以補齊 WIP",
        )

    requested_experiments = parse_requested_experiments_from_sample(sample)

    if len(requested_experiments) == 0:
        raise HTTPException(
            status_code=400,
            detail="找不到 requested_experiments，請確認這筆樣品是從 /others 新增委託單產生",
        )

    created_wips = []
    skipped_wips = []

    next_location = sample.get("current_location") or experiment_temp_location(
        current_user.get("lab_name") or current_user.get("department")
    )

    for index, item in enumerate(requested_experiments, start=1):
        lab_name = item["lab_name"]
        experiment_item = item["experiment_item"]

        exists = db.execute(
            text(
                """
                SELECT *
                FROM wips
                WHERE sample_id = :sample_id
                  AND lab_name = :lab_name
                  AND experiment_item = :experiment_item
                LIMIT 1
                """
            ),
            {
                "sample_id": sample_id,
                "lab_name": lab_name,
                "experiment_item": experiment_item,
            },
        ).fetchone()

        if exists is not None:
            skipped_wips.append(dict(exists._mapping))
            continue

        wip_no = generate_unique_wip_no(db, sample["sample_no"], index)

        wip_result = db.execute(
            text(
                """
                INSERT INTO wips (
                    wip_no,
                    sample_id,
                    order_no,
                    lab_name,
                    experiment_item,
                    priority,
                    status,
                    progress,
                    current_location,
                    note
                )
                VALUES (
                    :wip_no,
                    :sample_id,
                    :order_no,
                    :lab_name,
                    :experiment_item,
                    :priority,
                    'created',
                    0,
                    :current_location,
                    :note
                )
                RETURNING *
                """
            ),
            {
                "wip_no": wip_no,
                "sample_id": sample_id,
                "order_no": sample["order_no"],
                "lab_name": lab_name,
                "experiment_item": experiment_item,
                "priority": "normal",
                "current_location": next_location,
                "note": "由 /others 測試功能依委託單需求補齊 WIP",
            },
        )

        created_wip = dict(wip_result.fetchone()._mapping)
        created_wips.append(created_wip)

        db.execute(
            text(
                """
                INSERT INTO wip_histories (
                    wip_id,
                    action,
                    from_status,
                    to_status,
                    description,
                    operator_name
                )
                VALUES (
                    :wip_id,
                    'created_by_others_test',
                    NULL,
                    'created',
                    :description,
                    :operator_name
                )
                """
            ),
            {
                "wip_id": created_wip["id"],
                "description": (
                    f"由 /others 測試功能建立 WIP："
                    f"{lab_name} / {experiment_item}，位置：{next_location}"
                ),
                "operator_name": current_user["name"],
            },
        )

    db.execute(
        text(
            """
            UPDATE samples
            SET
                status = 'split',
                current_location = :current_location,
                updated_at = NOW()
            WHERE id = :sample_id
            """
        ),
        {
            "sample_id": sample_id,
            "current_location": next_location,
        },
    )

    db.execute(
        text(
            """
            INSERT INTO sample_histories (
                sample_id,
                action,
                from_status,
                to_status,
                description,
                operator_name,
                lab_name
            )
            VALUES (
                :sample_id,
                'generate_wips_by_others_test',
                :from_status,
                'split',
                :description,
                :operator_name,
                :lab_name
            )
            """
        ),
        {
            "sample_id": sample_id,
            "from_status": sample["status"],
            "description": f"由 /others 測試功能補齊 WIP，樣品狀態改為已分貨，位置：{next_location}",
            "operator_name": current_user["name"],
            "lab_name": current_user.get("lab_name") or current_user.get("department"),
        },
    )
    db.commit()

    return {
        "message": "WIP 補齊完成",
        "created_wips": created_wips,
        "skipped_wips": skipped_wips,
    }


@router.post("/others/wips/{wip_id}/complete")
def complete_wip_by_others_test(
    wip_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    current_user = resolve_current_user(request)

    wip_result = db.execute(
        text(
            """
            SELECT *
            FROM wips
            WHERE id = :wip_id
            """
        ),
        {"wip_id": wip_id},
    )

    wip_row = wip_result.fetchone()

    if wip_row is None:
        raise HTTPException(status_code=404, detail="WIP not found")

    wip = dict(wip_row._mapping)

    current_lab = current_user.get("lab_name") or current_user.get("department")
    next_location = experiment_temp_location(current_lab)

    result = db.execute(
        text(
            """
            UPDATE wips
            SET
                status = 'completed',
                progress = 100,
                completed_at = NOW(),
                current_location = :current_location,
                updated_at = NOW()
            WHERE id = :wip_id
            RETURNING *
            """
        ),
        {
            "wip_id": wip_id,
            "current_location": next_location,
        },
    )

    db.execute(
        text(
            """
            UPDATE samples
            SET
                current_location = :current_location,
                updated_at = NOW()
            WHERE id = :sample_id
            """
        ),
        {
            "sample_id": wip["sample_id"],
            "current_location": next_location,
        },
    )

    db.execute(
        text(
            """
            INSERT INTO wip_histories (
                wip_id,
                action,
                from_status,
                to_status,
                description,
                operator_name
            )
            VALUES (
                :wip_id,
                'complete_by_others_test',
                :from_status,
                'completed',
                :description,
                :operator_name
            )
            """
        ),
        {
            "wip_id": wip_id,
            "from_status": wip["status"],
            "description": f"由 /others 測試功能直接標記 WIP 完成，樣品回到 {next_location}",
            "operator_name": current_user["name"],
        },
    )

    db.commit()

    return {
        "message": "WIP 已標記完成",
        "wip": dict(result.fetchone()._mapping),
    }


@router.get("/master-data")
def get_master_data():
    return master_data


@router.get("/labs")
def get_labs():
    return mock_labs


@router.get("/storage-locations")
def get_storage_locations():
    return mock_storage_locations


@router.get("/orders/{order_no}")
def get_order(order_no: str):
    order = next(
        (
            item
            for item in mock_orders
            if item["order_no"] == order_no or item["id"] == order_no
        ),
        None,
    )

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    return order


@router.post("/orders/{order_no}/actions")
def order_action(order_no: str, payload: dict):
    order = get_order(order_no)

    return {
        "message": "Order action accepted by development mock route",
        "order": order,
        "action": payload.get("action"),
    }


@router.get("/schedules")
def get_schedules():
    return mock_schedules


@router.get("/dispatches")
def get_dispatches():
    return mock_dispatches


@router.get("/issues")
def get_issues():
    return mock_issues


@router.post("/issues")
def create_issue(payload: dict):
    return create_mock_issue(payload)

@router.post("/others/orders/{order_id}/confirm-delivery")
def confirm_mock_order_delivery(
    order_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    current_user = resolve_current_user(request)

    order = next(
        (
            item
            for item in mock_orders
            if item.get("id") == order_id or item.get("order_no") == order_id
        ),
        None,
    )

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.get("status") != "approved":
        raise HTTPException(
            status_code=400,
            detail="只有 approved 狀態的委託單可以確認送樣",
        )

    existing_sample = db.execute(
        text(
            """
            SELECT *
            FROM samples
            WHERE order_no = :order_no
            LIMIT 1
            """
        ),
        {"order_no": order["order_no"]},
    ).fetchone()

    if existing_sample is not None:
        order["status"] = "pending_receive"

        return {
            "order": order,
            "sample": dict(existing_sample._mapping),
            "message": "這張委託單已經有 sample，已標記為 pending_receive",
        }

    requested_experiments = order.get("requested_experiments") or []

    if not requested_experiments:
        requested_experiments = [
            {
                "lab_name": order.get("target_lab") or "Lab A",
                "experiment_item": order.get("test_item") or "SEM 觀察",
            }
        ]

    experiment_summary = "、".join(
        [
            f"{item.get('lab_name')}:{item.get('experiment_item')}"
            for item in requested_experiments
        ]
    )

    first_lab = requested_experiments[0].get("lab_name", "Lab A")
    sample_no = generate_sample_no(db)
    current_location = receive_location(first_lab)

    note = json.dumps(
        {
            "source": "/api/others/orders/confirm-delivery",
            "sample_quantity": order.get("sample_quantity") or "1",
            "priority": order.get("priority") or "normal",
            "requested_experiments": requested_experiments,
            "delivery_status": "confirmed",
        },
        ensure_ascii=False,
    )

    sample_result = db.execute(
        text(
            """
            INSERT INTO samples (
                sample_no,
                order_no,
                sample_name,
                experiment_item,
                applicant_name,
                applicant_department,
                status,
                current_location,
                note
            )
            VALUES (
                :sample_no,
                :order_no,
                :sample_name,
                :experiment_item,
                :applicant_name,
                :applicant_department,
                'pending_receive',
                :current_location,
                :note
            )
            RETURNING *
            """
        ),
        {
            "sample_no": sample_no,
            "order_no": order["order_no"],
            "sample_name": order.get("sample_name") or "未命名樣品",
            "experiment_item": experiment_summary,
            "applicant_name": order.get("applicant_name") or current_user["name"],
            "applicant_department": order.get("applicant_department") or current_user.get("department"),
            "current_location": current_location,
            "note": note,
        },
    )

    sample = dict(sample_result.fetchone()._mapping)

    db.execute(
        text(
            """
            INSERT INTO sample_histories (
                sample_id,
                action,
                from_status,
                to_status,
                description,
                operator_name,
                lab_name
            )
            VALUES (
                :sample_id,
                'delivery_confirmed_create_sample',
                NULL,
                'pending_receive',
                :description,
                :operator_name,
                :lab_name
            )
            """
        ),
        {
            "sample_id": sample["id"],
            "description": (
                f"廠區確認送樣，產生待收樣樣品 {sample_no}，"
                f"位置：{current_location}"
            ),
            "operator_name": current_user["name"],
            "lab_name": first_lab,
        },
    )
    order["status"] = "pending_receive"

    db.commit()

    return {
        "order": order,
        "sample": sample,
        "message": "已確認送樣，並建立待收樣 sample",
    }
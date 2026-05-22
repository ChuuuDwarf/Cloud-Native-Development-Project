# TODO(integration): 這個 route 是暫時替代層，專案合併後預期會刪除。
# 目前提供 role/order/system_setting/schedule/warn 等模組尚未完成時的 mock API。
# 後續請依 sample_management.md 改接：
# - role.md: GET /api/me
# - order_management.md: GET /api/orders/:id, POST /api/orders/:id/actions
# - system_setting.md: GET /api/storage-locations, GET /api/labs, GET /api/master-data
# - schedule.md: GET /api/schedules, GET /api/dispatches
# - warn.md: GET /api/issues, POST /api/issues
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db

router = APIRouter(
    prefix="/api",
    tags=["others"],
)


# 這個 route 檔現在只保留 API endpoint 與 request/response 組裝。
# 權限、位置、ID、狀態流轉等 helper 已拆到 service 檔，方便後續維護與測試。
from app.services.temporary_others_service import *  # noqa: F403 - route endpoint 會使用拆出的 helper

# TODO(integration): 改接 role.md 的 GET /api/me。
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


# TODO(integration): 改接 system_setting.md 的 GET /api/master-data。
@router.get("/master-data")
def get_master_data():
    return master_data


# TODO(integration): 改接 system_setting.md 的 GET /api/labs。
@router.get("/labs")
def get_labs():
    return mock_labs


# TODO(integration): 改接 system_setting.md 的 GET /api/storage-locations。
@router.get("/storage-locations")
def get_storage_locations():
    return mock_storage_locations


# TODO(integration): 改接 order_management.md 的 GET /api/orders/:id。
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


# TODO(integration): 改接 order_management.md 的 POST /api/orders/:id/actions。
@router.post("/orders/{order_no}/actions")
def order_action(order_no: str, payload: dict):
    order = get_order(order_no)

    return {
        "message": "Order action accepted by development mock route",
        "order": order,
        "action": payload.get("action"),
    }


# TODO(integration): 改接 schedule.md 的 GET /api/schedules。
@router.get("/schedules")
def get_schedules():
    return mock_schedules


# TODO(integration): 改接 schedule.md 的 GET /api/dispatches。
@router.get("/dispatches")
def get_dispatches():
    return mock_dispatches


# TODO(integration): 改接 warn.md 的 GET /api/issues。
@router.get("/issues")
def get_issues():
    return mock_issues


# TODO(integration): 改接 warn.md 的 POST /api/issues。
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
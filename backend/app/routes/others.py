from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.wip_service import (
    build_ordered_wip_slots,
    get_creatable_wip_slots_for_current_segment,
    get_sample_wips_in_flow_order,
    update_sample_to_pending_transfer_if_ready,
    validate_wip_can_complete_in_order,
)
from app.services.temporary_others_service import (
    experiment_temp_location,
    get_generated_storage_locations,
    get_real_labs,
    get_real_order,
    get_real_orders,
    get_real_users,
    generate_sample_no,
    generate_unique_wip_no,
    master_data,
    normalize_requested_experiments,
    parse_requested_experiments_from_sample,
    receive_location,
    removed_endpoint_response,
    resolve_current_user,
    resolve_real_lab_name,
)

router = APIRouter(
    prefix="/api",
    tags=["others"],
)


@router.get("/me")
async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    return await resolve_current_user(db, request)


@router.get("/others")
async def get_others(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    sample_result = await db.execute(
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

    wip_result = await db.execute(
        text(
            """
            SELECT
                w.id,
                w.wip_no,
                w.sample_id,
                w.order_no,
                w.lab_name,
                COALESCE(l.name, w.lab_name) AS real_lab_name,
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
            LEFT JOIN labs l
                ON CAST(l.id AS TEXT) = w.lab_name
                OR l.code = w.lab_name
                OR l.name = w.lab_name
            ORDER BY w.created_at DESC
            LIMIT 100
            """
        )
    )
    wips = [dict(row._mapping) for row in wip_result]

    labs = await get_real_labs(db)
    storage_locations = await get_generated_storage_locations(db)
    current_user = await resolve_current_user(db, request)

    try:
        users = await get_real_users(db)
    except Exception:
        await db.rollback()
        users = []

    try:
        orders = await get_real_orders(db)
    except Exception:
        await db.rollback()
        orders = []

    return {
        "current_user": current_user,
        "users": users,
        "labs": labs,
        "storage_locations": storage_locations,
        "orders": orders,
        "samples": samples,
        "wips": wips,
        # 這些模組如果還沒正式 DB，先回傳空陣列，不再吃 mock。
        "schedules": [],
        "dispatches": [],
        "issues": [],
        "master_data": master_data,
    }


# mock user 已移除。這支保留路由避免前端打到時 NameError，但明確回 410。
@router.post("/others/users")
def create_user_removed(payload: dict):
    return removed_endpoint_response("POST /api/others/users")


# mock lab 已移除。請使用正式 labs table。
@router.post("/others/labs")
def create_lab_removed(payload: dict):
    return removed_endpoint_response("POST /api/others/labs")


# storage_locations 目前由 labs 自動產生，不再允許新增 mock storage。
@router.post("/others/storage-locations")
def create_storage_location_removed(payload: dict):
    return removed_endpoint_response("POST /api/others/storage-locations")


@router.post("/others/orders")
def create_order_removed(payload: dict):
    return removed_endpoint_response("POST /api/others/orders")


@router.post("/others/schedules")
def create_schedule_removed(payload: dict):
    return removed_endpoint_response("POST /api/others/schedules")


@router.post("/others/dispatches")
def create_dispatch_removed(payload: dict):
    return removed_endpoint_response("POST /api/others/dispatches")


@router.post("/others/issues")
def create_issue_removed(payload: dict):
    return removed_endpoint_response("POST /api/others/issues")


@router.post("/others/master-data")
def create_master_data_removed(payload: dict):
    return removed_endpoint_response("POST /api/others/master-data")


@router.post("/others/samples/{sample_id}/generate-wips")
async def generate_missing_wips_for_sample(
    sample_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    current_user = await resolve_current_user(db, request)

    sample_result = await db.execute(
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

    if sample["status"] not in ("received", "split", "pending_transfer"):
        raise HTTPException(
            status_code=400,
            detail="只有已收樣 received、已分貨 split 或可交接 pending_transfer 的樣品可以補齊 WIP",
        )

    requested_experiments = parse_requested_experiments_from_sample(sample)

    if len(requested_experiments) == 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "找不到 requested_experiments，請確認 samples.experiment_item 格式是否正確，"
                "例如：材料分析實驗室:SEM 觀察、電性測試實驗室:光學量測"
            ),
        )

    normalized_requested_experiments = []

    for item in requested_experiments:
        lab_name = await resolve_real_lab_name(db, item["lab_name"])

        if not lab_name:
            raise HTTPException(
                status_code=400,
                detail=f"無法解析實驗室名稱：{item['lab_name']}",
            )

        normalized_requested_experiments.append(
            {
                "lab_name": lab_name,
                "experiment_item": item["experiment_item"],
            }
        )

    existing_sample_wips = await get_sample_wips_in_flow_order(sample_id, db)
    ordered_slots = build_ordered_wip_slots(
        normalized_requested_experiments,
        existing_sample_wips,
    )
    requested_experiments = [
        slot["experiment"]
        for slot in get_creatable_wip_slots_for_current_segment(ordered_slots)
    ]

    if len(requested_experiments) == 0:
        raise HTTPException(
            status_code=400,
            detail="目前尚未輪到此 WIP，請先完成前一站實驗或交接流程",
        )

    created_wips = []
    skipped_wips = []

    for index, item in enumerate(requested_experiments, start=1):
        raw_lab_name = item["lab_name"]
        experiment_item = item["experiment_item"]
        lab_name = await resolve_real_lab_name(db, raw_lab_name)

        if not lab_name:
            raise HTTPException(
                status_code=400,
                detail=f"無法解析實驗室名稱：{raw_lab_name}",
            )

        exists_result = await db.execute(
            text(
                """
                SELECT *
                FROM wips
                WHERE sample_id = :sample_id
                  AND (
                        lab_name = :raw_lab_name
                     OR lab_name = :lab_name
                  )
                  AND experiment_item = :experiment_item
                LIMIT 1
                """
            ),
            {
                "sample_id": sample_id,
                "raw_lab_name": raw_lab_name,
                "lab_name": lab_name,
                "experiment_item": experiment_item,
            },
        )
        exists = exists_result.fetchone()

        if exists is not None:
            skipped_wips.append(dict(exists._mapping))
            continue

        wip_no = await generate_unique_wip_no(
            db,
            sample["sample_no"],
            index,
            lab_name,
        )

        wip_location = experiment_temp_location(lab_name)

        wip_result = await db.execute(
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
                "current_location": wip_location,
                "note": "由 /others 功能依樣品實驗需求補齊 WIP",
            },
        )

        created_wip = dict(wip_result.fetchone()._mapping)
        created_wips.append(created_wip)

        await db.execute(
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
                    'created_by_others',
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
                    f"由 /others 功能建立 WIP："
                    f"{lab_name} / {experiment_item}，位置：{wip_location}"
                ),
                "operator_name": current_user.get("name") or "系統",
            },
        )

    sample_location = sample.get("current_location")

    if not sample_location:
        first_lab = await resolve_real_lab_name(db, requested_experiments[0]["lab_name"])
        sample_location = experiment_temp_location(first_lab)

    await db.execute(
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
            "current_location": sample_location,
        },
    )

    await db.execute(
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
                'generate_wips_by_others',
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
            "description": f"由 /others 功能補齊 WIP，樣品狀態改為已分貨，位置：{sample_location}",
            "operator_name": current_user.get("name") or "系統",
            "lab_name": await resolve_real_lab_name(db, requested_experiments[0]["lab_name"]),
        },
    )

    await db.commit()

    return {
        "message": "WIP 補齊完成",
        "created_wips": created_wips,
        "skipped_wips": skipped_wips,
    }


@router.post("/others/wips/{wip_id}/complete")
async def complete_wip_by_others_test(
    wip_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    current_user = await resolve_current_user(db, request)
    operator_name = current_user.get("name") or "系統"

    wip_result = await db.execute(
        text(
            """
            SELECT
                w.*,
                COALESCE(l.name, w.lab_name) AS real_lab_name
            FROM wips w
            LEFT JOIN labs l
                ON CAST(l.id AS TEXT) = w.lab_name
                OR l.code = w.lab_name
                OR l.name = w.lab_name
            WHERE w.id = :wip_id
            LIMIT 1
            """
        ),
        {"wip_id": wip_id},
    )

    wip_row = wip_result.fetchone()

    if wip_row is None:
        raise HTTPException(status_code=404, detail="WIP not found")

    wip = dict(wip_row._mapping)
    current_lab = wip.get("real_lab_name")

    if not current_lab:
        raise HTTPException(
            status_code=400,
            detail="WIP lab_name is missing or cannot resolve real lab name",
        )

    next_location = experiment_temp_location(current_lab)
    wip_flow_index = await validate_wip_can_complete_in_order(db, wip)

    result = await db.execute(
        text(
            """
            UPDATE wips
            SET
                lab_name = :lab_name,
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
            "lab_name": current_lab,
            "current_location": next_location,
        },
    )

    updated_wip = dict(result.fetchone()._mapping)

    await db.execute(
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

    await update_sample_to_pending_transfer_if_ready(
        db=db,
        sample_id=wip["sample_id"],
        current_lab=current_lab,
        next_location=next_location,
        operator_name=operator_name,
        completed_wip=updated_wip,
        completed_wip_index=wip_flow_index,
    )

    await db.execute(
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
                'complete_by_others',
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
            "description": f"標記 WIP 完成，樣品回到 {next_location}",
            "operator_name": operator_name,
        },
    )

    await db.commit()

    return {
        "message": "WIP 已標記完成",
        "wip": updated_wip,
    }


@router.get("/master-data")
def get_master_data():
    return master_data


@router.get("/labs")
async def get_labs(db: AsyncSession = Depends(get_db)):
    return await get_real_labs(db)


@router.get("/storage-locations")
async def get_storage_locations(db: AsyncSession = Depends(get_db)):
    return await get_generated_storage_locations(db)


@router.get("/orders/{order_no}")
async def get_order(
    order_no: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        order = await get_real_order(db, order_no)
    except Exception:
        await db.rollback()
        order = None

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    return order


@router.post("/orders/{order_no}/actions")
def order_action_removed(order_no: str, payload: dict):
    return removed_endpoint_response("POST /api/orders/{order_no}/actions")


@router.get("/schedules")
def get_schedules():
    return []


@router.get("/dispatches")
def get_dispatches():
    return []


@router.get("/issues")
def get_issues():
    return []


@router.post("/issues")
def create_issue(payload: dict):
    return removed_endpoint_response("POST /api/issues")


@router.post("/others/orders/{order_id}/confirm-delivery")
async def confirm_order_delivery(
    order_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    current_user = await resolve_current_user(db, request)

    try:
        order = await get_real_order(db, order_id)
    except Exception:
        await db.rollback()
        order = None

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    status = order.get("status")

    if status not in ("approved", "pending_receive"):
        raise HTTPException(
            status_code=400,
            detail="只有 approved 或 pending_receive 狀態的委託單可以確認送樣",
        )

    existing_sample_result = await db.execute(
        text(
            """
            SELECT *
            FROM samples
            WHERE order_no = :order_no
            LIMIT 1
            """
        ),
        {"order_no": order["order_no"]},
    )
    existing_sample = existing_sample_result.fetchone()

    if existing_sample is not None:
        return {
            "order": order,
            "sample": dict(existing_sample._mapping),
            "message": "這張委託單已經有 sample",
        }

    requested_experiments = normalize_requested_experiments(
        order.get("requested_experiments")
        or order.get("experiment_items")
        or order.get("experiment_item")
    )

    if not requested_experiments:
        target_lab = order.get("target_lab") or order.get("lab_name")
        test_item = order.get("test_item") or order.get("experiment_item")

        if target_lab and test_item:
            requested_experiments = [
                {
                    "lab_name": target_lab,
                    "experiment_item": test_item,
                }
            ]

    if not requested_experiments:
        raise HTTPException(
            status_code=400,
            detail="找不到委託單的實驗需求，無法建立 sample",
        )

    normalized_experiments = []

    for item in requested_experiments:
        lab_name = await resolve_real_lab_name(db, item["lab_name"])

        if not lab_name:
            raise HTTPException(
                status_code=400,
                detail=f"無法解析實驗室名稱：{item['lab_name']}",
            )

        normalized_experiments.append(
            {
                "lab_name": lab_name,
                "experiment_item": item["experiment_item"],
            }
        )

    experiment_summary = "、".join(
        [
            f"{item['lab_name']}:{item['experiment_item']}"
            for item in normalized_experiments
        ]
    )

    first_lab = normalized_experiments[0]["lab_name"]
    sample_no = await generate_sample_no(db)
    current_location = receive_location(first_lab)

    sample_result = await db.execute(
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
            "sample_name": order.get("sample_name") or order.get("name") or "未命名樣品",
            "experiment_item": experiment_summary,
            "applicant_name": order.get("applicant_name") or current_user.get("name") or "未命名申請人",
            "applicant_department": order.get("applicant_department") or current_user.get("department"),
            "current_location": current_location,
            "note": order.get("note"),
        },
    )

    sample = dict(sample_result.fetchone()._mapping)

    await db.execute(
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
                f"已確認送樣，樣品 {sample_no} 正在等待實驗室收樣，"
                f"目前位置：{current_location}"
            ),
            "operator_name": current_user.get("name") or "系統",
            "lab_name": first_lab,
        },
    )

    await db.commit()

    return {
        "order": order,
        "sample": sample,
        "message": "已確認送樣，樣品已進入待收樣流程",
    }

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import CurrentUser, get_current_user
from app.core.database import get_db
from app.db.models.departments import Department
from app.db.models.labs import Lab

router = APIRouter(
    prefix="/api/samples",
    tags=["samples"],
)


# 這個 route 檔現在只保留 API endpoint 與 request/response 組裝。
# 權限、位置、ID、狀態流轉等 helper 已拆到 service 檔，方便後續維護與測試。
from app.services.sample_service import *  # noqa: F403 - route endpoint 會使用拆出的 helper


ROLE_LABELS = {
    "system_admin": "系統管理者",
    "lab_supervisor": "實驗室主管",
    "lab_engineer": "實驗室人員",
    "plant_user": "廠區使用者",
}


async def build_sample_current_user(current_user: CurrentUser, db: AsyncSession) -> dict:
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
        "department": department_name or "",
        "lab_name": lab_name,
        "email": current_user.email,
    }


def parse_required_labs_from_experiment_item(experiment_item: str | None):
    """
    從 sample.experiment_item 解析需要流轉的 Lab 順序。

    格式範例：
    Lab A:SEM 觀察、Lab B:光學量測

    回傳：
    ["Lab A", "Lab B"]
    """
    if not experiment_item:
        return []

    required_labs = []

    for part in experiment_item.split("、"):
        part = part.strip()

        if ":" not in part:
            continue

        lab_name = part.split(":", 1)[0].strip()

        if lab_name and lab_name not in required_labs:
            required_labs.append(lab_name)

    return required_labs


def get_next_lab_after_current(experiment_item: str | None, current_lab: str | None):
    if not current_lab:
        return None

    required_labs = parse_required_labs_from_experiment_item(experiment_item)

    if current_lab not in required_labs:
        return None

    current_index = required_labs.index(current_lab)

    if current_index >= len(required_labs) - 1:
        return None

    return required_labs[current_index + 1]


def parse_requested_experiments_from_summary(experiment_item: str | None):
    if not experiment_item:
        return []

    experiments = []

    for part in experiment_item.split("、"):
        part = part.strip()
        if ":" not in part:
            continue

        lab_name, experiment_name = part.split(":", 1)
        lab_name = lab_name.strip()
        experiment_name = experiment_name.strip()

        if lab_name and experiment_name:
            experiments.append(
                {
                    "lab_name": lab_name,
                    "experiment_item": experiment_name,
                }
            )

    return experiments


def normalize_flow_value(value: str | None):
    return (value or "").strip().lower()


@router.get("")
async def get_samples(
    status: str | None = Query(default=None),
    scope: str | None = Query(default=None),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sample_current_user = await build_sample_current_user(current_user, db)
    where_clauses, params = build_sample_visibility_filter(sample_current_user, scope)

    if status:
        where_clauses.append("s.status = :status")
        params["status"] = status

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    result = await db.execute(
        text(
            f"""
            SELECT
                s.id,
                s.sample_no,
                s.order_no,
                s.sample_name,
                s.experiment_item,
                s.applicant_name,
                COALESCE(department.name, s.applicant_department) AS applicant_department,
                s.status,
                s.current_location,
                s.storage_location_id,
                s.received_at,
                s.received_by,
                s.picked_up_at,
                s.picked_up_by,
                s.note,
                s.created_at,
                s.updated_at
            FROM samples s
            LEFT JOIN departments department
                ON CAST(department.id AS TEXT) = s.applicant_department
                OR department.code = s.applicant_department
            {where_sql}
            ORDER BY s.created_at DESC
            """
        ),
        params,
    )

    return [dict(row._mapping) for row in result]


@router.get("/{sample_id}")
async def get_sample(
    sample_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sample_current_user = await build_sample_current_user(current_user, db)
    sample = await get_sample_or_404(sample_id, db)

    if not await can_view_sample(sample_current_user, sample, db):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view this sample",
        )

    return sample


@router.get("/{sample_id}/history")
async def get_sample_history(
    sample_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sample_current_user = await build_sample_current_user(current_user, db)
    sample = await get_sample_or_404(sample_id, db)

    if not await can_view_sample(sample_current_user, sample, db):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view this sample",
        )

    role = sample_current_user.get("role")
    current_lab = get_user_lab(sample_current_user)

    where_clauses = ["h.sample_id = :sample_id"]
    params = {"sample_id": sample_id}

    if is_factory_role(role):
        if sample.get("applicant_name") != sample_current_user.get("name"):
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to view this sample history",
            )

    elif role in ("system_admin", "lab_supervisor"):
        pass

    elif role == "lab_engineer":
        if not current_lab:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to view this sample history",
            )

        params["current_lab"] = current_lab

        where_clauses.append(
            """
            (
                h.lab_name = :current_lab
                OR h.created_at <= (
                    SELECT MIN(COALESCE(t.received_at, t.transferred_at, t.updated_at, t.created_at))
                    FROM transfers t
                    WHERE t.target_type = 'sample'
                      AND t.target_id = :sample_id
                      AND t.to_lab = :current_lab
                )
            )
            """
        )

    else:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view this sample history",
        )

    where_sql = "WHERE " + " AND ".join(where_clauses)

    result = await db.execute(
        text(
            f"""
            SELECT
                h.id,
                h.sample_id,
                h.action,
                h.from_status,
                h.to_status,
                h.description,
                h.operator_name,
                h.lab_name,
                h.created_at
            FROM sample_histories h
            {where_sql}
            ORDER BY h.created_at DESC
            """
        ),
        params,
    )

    return [dict(row._mapping) for row in result]

@router.patch("/{sample_id}")
async def update_sample(
    sample_id: str,
    payload: dict,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sample_current_user = await build_sample_current_user(current_user, db)
    sample = await get_sample_or_404(sample_id, db)

    if not can_manage_sample(sample_current_user, sample):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to update this sample",
        )

    result = await db.execute(
        text(
            """
            UPDATE samples
            SET
                sample_name = COALESCE(:sample_name, sample_name),
                experiment_item = COALESCE(:experiment_item, experiment_item),
                current_location = COALESCE(:current_location, current_location),
                note = COALESCE(:note, note),
                updated_at = NOW()
            WHERE id = :sample_id
            RETURNING *
            """
        ),
        {
            "sample_id": sample_id,
            "sample_name": payload.get("sample_name"),
            "experiment_item": payload.get("experiment_item"),
            "current_location": payload.get("current_location"),
            "note": payload.get("note"),
        },
    )

    await db.commit()

    return dict(result.fetchone()._mapping)


# TODO(integration): sample actions 目前直接在此 route 執行收樣、分貨、交接、入庫、出庫、取件。
# 正式模組合併後，若流程需要同步委託單/通知/排程，請改接對應模組 service 或 API。
@router.post("/{sample_id}/actions")
async def sample_action(
    sample_id: str,
    payload: dict,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sample = await get_sample_or_404(sample_id, db)
    sample_current_user = await build_sample_current_user(current_user, db)

    current_lab = get_user_lab(sample_current_user)
    action = payload.get("action")

    if action not in (
        "receive",
        "inbound",
        "outbound",
        "pickup_confirmed",
        "split",
    ):
        raise HTTPException(
            status_code=400,
            detail="action must be one of: receive, inbound, outbound, pickup_confirmed, split",
        )

    can_operate = can_manage_sample(sample_current_user, sample)
    can_pickup = action == "pickup_confirmed" and can_confirm_pickup(sample_current_user, sample)

    if not can_operate and not can_pickup:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to operate this sample",
        )

    if is_factory_role(sample_current_user.get("role")) and action != "pickup_confirmed":
        raise HTTPException(
            status_code=403,
            detail="廠區使用者只能在待取件狀態確認取件",
        )

    operator_name = payload.get("operator_name") or sample_current_user.get("name")

    if not operator_name:
        raise HTTPException(
            status_code=400,
            detail="operator_name is required",
        )

    if action == "receive":
        if sample["status"] not in ("pending_receive", "transferring"):
            raise HTTPException(
                status_code=400,
                detail="只有待收樣或交接中的樣品可以確認收樣",
            )

        transfer_for_receive_result = await db.execute(
            text(
                """
                SELECT *
                FROM transfers
                WHERE target_type = 'sample'
                  AND target_id = :sample_id
                  AND to_lab = :current_lab
                  AND status = 'transferring'
                ORDER BY transferred_at DESC NULLS LAST, created_at DESC
                LIMIT 1
                """
            ),
            {
                "sample_id": sample_id,
                "current_lab": current_lab,
            },
        )
        transfer_for_receive = transfer_for_receive_result.fetchone()

        transfer_for_receive_data = (
            dict(transfer_for_receive._mapping)
            if transfer_for_receive is not None
            else None
        )

        next_location = normalize_location_for_action(
            payload.get("current_location"),
            current_lab,
            "實驗暫存區",
        )

        result = await db.execute(
            text(
                """
                UPDATE samples
                SET
                    status = 'received',
                    current_location = :next_location,
                    received_at = NOW(),
                    received_by = :operator_name,
                    updated_at = NOW()
                WHERE id = :sample_id
                RETURNING *
                """
            ),
            {
                "sample_id": sample_id,
                "next_location": next_location,
                "operator_name": operator_name,
            },
        )

        await update_current_lab_wips_location(
            db=db,
            sample_id=sample_id,
            current_lab=current_lab,
            next_location=next_location,
        )

        await db.execute(
            text(
                """
                UPDATE transfers
                SET
                    status = 'received',
                    received_by = :operator_name,
                    received_at = NOW(),
                    updated_at = NOW()
                WHERE target_type = 'sample'
                  AND target_id = :sample_id
                  AND to_lab = :current_lab
                  AND status = 'transferring'
                """
            ),
            {
                "sample_id": sample_id,
                "current_lab": current_lab,
                "operator_name": operator_name,
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
                    'receive',
                    :from_status,
                    'received',
                    :description,
                    :operator_name,
                    :lab_name
                )
                """
            ),
            {
                "sample_id": sample_id,
                "from_status": sample["status"],
                "description": f"確認收樣，樣品移至 {next_location}",
                "operator_name": operator_name,
                "lab_name": current_lab,
            },
        )

        if transfer_for_receive_data is not None:
            from_lab = transfer_for_receive_data.get("from_lab")
            to_lab = transfer_for_receive_data.get("to_lab")
            transfer_no = transfer_for_receive_data.get("transfer_no")

            if from_lab and from_lab != current_lab:
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
                            'transfer_received_by_next_lab',
                            :from_status,
                            'received',
                            :description,
                            :operator_name,
                            :lab_name
                        )
                        """
                    ),
                    {
                        "sample_id": sample_id,
                        "from_status": sample["status"],
                        "description": (
                            f"交接單 {transfer_no} 已由 {to_lab} 確認收樣，"
                            f"樣品已送達對方實驗室"
                        ),
                        "operator_name": operator_name,
                        "lab_name": from_lab,
                    },
                )

        await db.commit()

        return dict(result.fetchone()._mapping)

    if action == "inbound":
        storage_location_id = payload.get("storage_location_id")

        if storage_location_id:
            validate_uuid(storage_location_id, "storage_location_id")

        result = await db.execute(
            text(
                """
                UPDATE samples
                SET
                    status = 'in_storage',
                    current_location = COALESCE(:current_location, current_location),
                    storage_location_id = COALESCE(:storage_location_id, storage_location_id),
                    updated_at = NOW()
                WHERE id = :sample_id
                RETURNING *
                """
            ),
            {
                "sample_id": sample_id,
                "current_location": payload.get("current_location"),
                "storage_location_id": storage_location_id,
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
                    'inbound',
                    :from_status,
                    'in_storage',
                    '樣品入庫',
                    :operator_name,
                    :lab_name
                )
                """
            ),
            {
                "sample_id": sample_id,
                "from_status": sample["status"],
                "operator_name": operator_name,
                "lab_name": current_lab,
            },
        )

        await db.commit()

        return dict(result.fetchone()._mapping)

    if action == "outbound":
        if sample["status"] not in ("split", "pending_transfer"):
            raise HTTPException(
                status_code=400,
                detail="只有已建立 WIP / 已分貨的樣品可以通知取件",
            )

        pending_transfer_result = await db.execute(
            text(
                """
                SELECT
                    transfer_no,
                    from_lab,
                    to_lab,
                    status
                FROM transfers
                WHERE target_type = 'sample'
                  AND target_id = :sample_id
                  AND status IN ('pending', 'transferring')
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {"sample_id": sample_id},
        )
        pending_transfer = pending_transfer_result.fetchone()

        if pending_transfer is not None:
            pending_transfer_data = dict(pending_transfer._mapping)

            raise HTTPException(
                status_code=400,
                detail=(
                    "此樣品仍有尚未完成的交接流程，不能通知取件："
                    f"{pending_transfer_data.get('transfer_no')} "
                    f"{pending_transfer_data.get('from_lab')} → "
                    f"{pending_transfer_data.get('to_lab')} "
                    f"({pending_transfer_data.get('status')})"
                ),
            )

        incomplete_wips_result = await db.execute(
            text(
                """
                SELECT
                    lab_name,
                    experiment_item,
                    status
                FROM wips
                WHERE sample_id = :sample_id
                  AND status <> 'completed'
                ORDER BY created_at ASC
                """
            ),
            {"sample_id": sample_id},
        )
        incomplete_wips = incomplete_wips_result.fetchall()

        if incomplete_wips:
            items = [
                f"{row._mapping['lab_name']} / {row._mapping['experiment_item']}：{row._mapping['status']}"
                for row in incomplete_wips
            ]

            raise HTTPException(
                status_code=400,
                detail=f"此樣品仍有未完成的 WIP，不能通知取件：{'、'.join(items)}",
            )

        completed_wips_result = await db.execute(
            text(
                """
                SELECT
                    lab_name,
                    experiment_item
                FROM wips
                WHERE sample_id = :sample_id
                  AND status = 'completed'
                """
            ),
            {"sample_id": sample_id},
        )
        completed_wips = [
            {
                "lab_name": row._mapping["lab_name"],
                "experiment_item": row._mapping["experiment_item"],
            }
            for row in completed_wips_result.fetchall()
        ]

        next_unfinished_experiment = None
        for experiment in parse_requested_experiments_from_summary(sample.get("experiment_item")):
            completed = any(
                normalize_flow_value(wip["lab_name"]) == normalize_flow_value(experiment["lab_name"])
                and normalize_flow_value(wip["experiment_item"])
                == normalize_flow_value(experiment["experiment_item"])
                for wip in completed_wips
            )

            if not completed:
                next_unfinished_experiment = experiment
                break

        if next_unfinished_experiment:
            next_lab = next_unfinished_experiment["lab_name"]
            raise HTTPException(
                status_code=400,
                detail=(
                    f"此樣品後續還有 {next_lab} 的實驗，"
                    f"不能由 {current_lab} 通知取件，請先交接流轉"
                ),
            )

        next_location = normalize_location_for_action(
            payload.get("current_location"),
            current_lab,
            "待取件區",
        )

        result = await db.execute(
            text(
                """
                UPDATE samples
                SET
                    status = 'outbound',
                    current_location = :next_location,
                    note = COALESCE(:note, note),
                    updated_at = NOW()
                WHERE id = :sample_id
                RETURNING *
                """
            ),
            {
                "sample_id": sample_id,
                "next_location": next_location,
                "note": payload.get("note"),
            },
        )

        await update_all_wips_location(
            db=db,
            sample_id=sample_id,
            next_location=next_location,
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
                    'outbound',
                    :from_status,
                    'outbound',
                    :description,
                    :operator_name,
                    :lab_name
                )
                """
            ),
            {
                "sample_id": sample_id,
                "from_status": sample["status"],
                "description": f"通知原使用者取件，樣品移至 {next_location}",
                "operator_name": operator_name,
                "lab_name": current_lab,
            },
        )

        await db.commit()

        return dict(result.fetchone()._mapping)

    if action == "pickup_confirmed":
        if sample["status"] != "outbound":
            raise HTTPException(
                status_code=400,
                detail="只有待取件 outbound 狀態可以確認取件",
            )

        pickup_lab = get_lab_from_location(sample.get("current_location"))
        next_location = payload.get("current_location") or "已由使用者取回"

        result = await db.execute(
            text(
                """
                UPDATE samples
                SET
                    status = 'picked_up',
                    current_location = :next_location,
                    picked_up_at = NOW(),
                    picked_up_by = :operator_name,
                    updated_at = NOW()
                WHERE id = :sample_id
                RETURNING *
                """
            ),
            {
                "sample_id": sample_id,
                "next_location": next_location,
                "operator_name": operator_name,
            },
        )

        await update_all_wips_location(
            db=db,
            sample_id=sample_id,
            next_location=next_location,
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
                    'pickup_confirmed',
                    :from_status,
                    'picked_up',
                    '廠區確認取件，樣品已由使用者取回',
                    :operator_name,
                    :lab_name
                )
                """
            ),
            {
                "sample_id": sample_id,
                "from_status": sample["status"],
                "operator_name": operator_name,
                "lab_name": pickup_lab,
            },
        )

        await db.commit()

        return dict(result.fetchone()._mapping)

    if action == "split":
        wips = payload.get("wips")

        if not isinstance(wips, list) or len(wips) == 0:
            raise HTTPException(
                status_code=400,
                detail="wips must be a non-empty list when action is split",
            )

        next_location = normalize_location_for_action(
            payload.get("current_location"),
            current_lab,
            "實驗暫存區",
        )

        created_wips = []

        await db.execute(
            text(
                """
                UPDATE samples
                SET
                    status = 'split',
                    current_location = :next_location,
                    updated_at = NOW()
                WHERE id = :sample_id
                """
            ),
            {
                "sample_id": sample_id,
                "next_location": next_location,
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
                    'split',
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
                "description": f"樣品分貨並建立 WIP，樣品位於 {next_location}",
                "operator_name": operator_name,
                "lab_name": current_lab,
            },
        )

        for item in wips:
            lab_name = item.get("lab_name")
            experiment_item = item.get("experiment_item")

            if not lab_name:
                raise HTTPException(
                    status_code=400,
                    detail="lab_name is required for each WIP",
                )

            if not experiment_item:
                raise HTTPException(
                    status_code=400,
                    detail="experiment_item is required for each WIP",
                )

            existing_wip_result = await db.execute(
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
            )
            existing_wip = existing_wip_result.fetchone()

            if existing_wip is not None:
                created_wips.append(dict(existing_wip._mapping))
                continue

            wip_no = await generate_unique_wip_no(
                db=db,
                sample=sample,
                lab_name=lab_name,
                preferred_wip_no=item.get("wip_no"),
            )

            result = await db.execute(
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
                    "priority": item.get("priority", "normal"),
                    "current_location": item.get("current_location") or next_location,
                    "note": item.get("note"),
                },
            )

            created_wip = dict(result.fetchone()._mapping)
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
                        'created_from_split',
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
                        f"由樣品 {sample['sample_no']} 分貨建立 WIP："
                        f"{lab_name} / {experiment_item}，位置：{next_location}"
                    ),
                    "operator_name": operator_name,
                },
            )

        await db.commit()

        return {
            "message": "Sample split successfully",
            "sample_id": sample_id,
            "current_location": next_location,
            "created_wips": created_wips,
        }

    raise HTTPException(status_code=400, detail="Unsupported action")

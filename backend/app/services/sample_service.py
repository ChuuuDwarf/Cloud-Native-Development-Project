from uuid import UUID

from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.repos import sample_repo, transfer_repo
from app.services.wip_service import (
    normalize_flow_value,
    parse_requested_experiments,
    validate_wip_create_items_in_order,
)


fallback_user = {
    "id": "system",
    "name": "系統",
    "role": "system_admin",
    "role_name": "系統管理者",
    "department": None,
    "lab_name": None,
    "email": "",
}


async def get_active_user(
    db: AsyncSession,
    request: Request | None = None,
):
    """讀正式目前使用者；不再依賴 mock user。"""
    try:
        from app.services.temporary_others_service import resolve_current_user

        return await resolve_current_user(db, request)
    except Exception:
        await db.rollback()
        return fallback_user


def get_user_lab(user: dict):
    return user.get("lab_name") or user.get("department")


def get_lab_from_location(location: str | None):
    """從位置字串推回 lab 名稱。

    以前只支援 Lab A/B/C，現在改成支援正式 lab name：
    例如「材料分析實驗室 實驗暫存區」=>「材料分析實驗室」。
    """
    if not location:
        return None

    location = location.strip()
    area_suffixes = [
        "收樣區",
        "實驗暫存區",
        "機台區",
        "交接待送區",
        "待取件區",
    ]

    for area in area_suffixes:
        suffix = f" {area}"
        if location.endswith(suffix):
            return location[: -len(suffix)].strip() or None

    return None


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


def machine_location(lab_name: str | None):
    return lab_location(lab_name, "機台區")


def transfer_waiting_location(lab_name: str | None):
    return lab_location(lab_name, "交接待送區")


def pickup_location(lab_name: str | None):
    return lab_location(lab_name, "待取件區")


def normalize_location_for_action(
    payload_location: str | None,
    current_lab: str | None,
    default_area: str,
):
    if payload_location:
        return payload_location

    return lab_location(current_lab, default_area)


def is_factory_role(role: str | None) -> bool:
    return role == "plant_user"


def is_lab_role(role: str | None) -> bool:
    return role in ("lab_engineer", "lab_supervisor")


def build_sample_visibility_filter(current_user: dict, scope: str | None = None):
    role = current_user.get("role")
    where_clauses = []
    params = {}

    if role == "system_admin":
        return where_clauses, params

    if is_factory_role(role):
        where_clauses.append("s.applicant_name = :applicant_name")
        params["applicant_name"] = current_user.get("name")
        return where_clauses, params

    if role == "lab_supervisor":
        current_lab = get_user_lab(current_user)

        if not current_lab:
            where_clauses.append("1 = 0")
            return where_clauses, params

        params["current_lab"] = current_lab
        params["current_lab_prefix"] = f"{current_lab}%"

        where_clauses.append(
            """
            (
                s.current_location LIKE :current_lab_prefix
                OR EXISTS (
                    SELECT 1
                    FROM wips w
                    WHERE w.sample_id = s.id
                      AND w.lab_name = :current_lab
                )
                OR EXISTS (
                    SELECT 1
                    FROM transfers t
                    WHERE t.target_type = 'sample'
                      AND t.target_id = s.id
                      AND (
                          t.from_lab = :current_lab
                          OR t.to_lab = :current_lab
                      )
                )
            )
            """
        )

        return where_clauses, params

    if role == "lab_engineer":
        current_lab = get_user_lab(current_user)

        if not current_lab:
            where_clauses.append("1 = 0")
            return where_clauses, params

        params["current_lab"] = current_lab
        params["current_lab_prefix"] = f"{current_lab}%"

        if scope == "all":
            where_clauses.append(
                """
                (
                    s.current_location LIKE :current_lab_prefix
                    OR EXISTS (
                        SELECT 1
                        FROM wips w
                        WHERE w.sample_id = s.id
                          AND w.lab_name = :current_lab
                    )
                    OR EXISTS (
                        SELECT 1
                        FROM transfers t
                        WHERE t.target_type = 'sample'
                          AND t.target_id = s.id
                          AND (
                              t.from_lab = :current_lab
                              OR t.to_lab = :current_lab
                          )
                    )
                )
                """
            )
            return where_clauses, params

        where_clauses.append("s.current_location LIKE :current_lab_prefix")
        return where_clauses, params

    where_clauses.append("1 = 0")
    return where_clauses, params


async def can_view_sample(
    current_user: dict,
    sample: dict,
    db: AsyncSession | None = None,
) -> bool:
    role = current_user.get("role")

    if role in ("system_admin", "lab_supervisor"):
        return True

    if is_factory_role(role):
        return sample.get("applicant_name") == current_user.get("name")

    if role == "lab_engineer":
        current_lab = get_user_lab(current_user)
        current_location = sample.get("current_location") or ""

        if current_lab and current_location.startswith(current_lab):
            return True

        if db is None or not current_lab:
            return False

        return await sample_repo.has_related_lab_sample_access(
            db,
            sample_id=sample.get("id"),
            current_lab=current_lab,
        )

    return False


def can_manage_sample(current_user: dict, sample: dict) -> bool:
    role = current_user.get("role")

    if role == "system_admin":
        return True

    if not is_lab_role(role) and role != "system_admin":
        return False

    current_lab = get_user_lab(current_user)
    current_location = sample.get("current_location") or ""

    return bool(current_lab and current_location.startswith(current_lab))


def can_confirm_pickup(current_user: dict, sample: dict) -> bool:
    return (
        is_factory_role(current_user.get("role"))
        and sample.get("applicant_name") == current_user.get("name")
        and sample.get("status") == "outbound"
    )


def validate_uuid(value: str | None, field_name: str) -> None:
    try:
        UUID(str(value))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must be a valid UUID",
        )


async def get_sample_or_404(sample_id: str, db: AsyncSession):
    validate_uuid(sample_id, "sample_id")

    sample = await sample_repo.get_sample_by_id(db, sample_id)

    if sample is None:
        raise HTTPException(status_code=404, detail="Sample not found")

    return sample


async def update_current_lab_wips_location(
    db: AsyncSession,
    sample_id: str,
    current_lab: str | None,
    next_location: str,
):
    await sample_repo.update_current_lab_wips_location(
        db,
        sample_id=sample_id,
        current_lab=current_lab,
        next_location=next_location,
    )


async def update_all_wips_location(
    db: AsyncSession,
    sample_id: str,
    next_location: str,
):
    await sample_repo.update_all_wips_location(
        db,
        sample_id=sample_id,
        next_location=next_location,
    )


def normalize_lab_code(lab_name: str | None):
    if not lab_name:
        return "LAB"

    cleaned = lab_name.strip().replace(" ", "")
    lowered = cleaned.lower()

    if lowered.startswith("laba"):
        return "A"

    if lowered.startswith("labb"):
        return "B"

    if lowered.startswith("labc"):
        return "C"

    if lowered.startswith("labd"):
        return "D"

    chinese_lab_code_map = {
        "材料分析實驗室": "A",
        "電性測試實驗室": "B",
        "可靠度實驗室": "C",
    }

    return chinese_lab_code_map.get(cleaned, cleaned.upper())


def normalize_lab_code_from_lab_code(lab_code: str | None):
    if not lab_code:
        return None

    cleaned = lab_code.strip().upper()

    if cleaned.startswith("LAB-") and len(cleaned) > 4:
        return cleaned.split("-", 1)[1]

    return cleaned


async def resolve_lab_code(db: AsyncSession, lab_name: str | None):
    if not lab_name:
        return "LAB"

    lab_code = await sample_repo.get_lab_code_by_name_or_code(
        db,
        lab_name=lab_name,
    )

    if lab_code:
        normalized_lab_code = normalize_lab_code_from_lab_code(lab_code)
        if normalized_lab_code:
            return normalized_lab_code

    return normalize_lab_code(lab_name)


async def generate_unique_wip_no(
    db: AsyncSession,
    sample: dict,
    lab_name: str | None,
    preferred_wip_no: str | None = None,
):
    sample_no = sample.get("sample_no") or "SMP"
    lab_code = await resolve_lab_code(db, lab_name)
    base_no = sample_no.replace("SMP-", "WIP-")

    for index in range(1, 1000):
        candidate = f"{base_no}-{lab_code}-{index:02d}"

        exists = await sample_repo.wip_no_exists(db, wip_no=candidate)
        if not exists:
            return candidate

    raise HTTPException(
        status_code=500,
        detail="Unable to generate unique WIP number",
    )


async def list_samples(
    db: AsyncSession,
    current_user: dict,
    status: str | None = None,
    scope: str | None = None,
):
    where_clauses, params = build_sample_visibility_filter(current_user, scope)

    if status:
        where_clauses.append("s.status = :status")
        params["status"] = status

    return await sample_repo.list_samples(
        db,
        where_clauses=where_clauses,
        params=params,
    )


async def get_sample_detail(
    db: AsyncSession,
    current_user: dict,
    sample_id: str,
):
    sample = await get_sample_or_404(sample_id, db)

    if not await can_view_sample(current_user, sample, db):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view this sample",
        )

    return sample


async def list_sample_history(
    db: AsyncSession,
    current_user: dict,
    sample_id: str,
):
    sample = await get_sample_or_404(sample_id, db)

    if not await can_view_sample(current_user, sample, db):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view this sample",
        )

    role = current_user.get("role")
    current_lab = get_user_lab(current_user)

    where_clauses = ["h.sample_id = :sample_id"]
    params = {"sample_id": sample_id}

    if is_factory_role(role):
        if sample.get("applicant_name") != current_user.get("name"):
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

    return await sample_repo.list_sample_history(
        db,
        where_clauses=where_clauses,
        params=params,
    )


async def update_sample(
    db: AsyncSession,
    current_user: dict,
    sample_id: str,
    payload: dict,
):
    sample = await get_sample_or_404(sample_id, db)

    if not can_manage_sample(current_user, sample):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to update this sample",
        )

    updated_sample = await sample_repo.update_sample_fields(
        db,
        sample_id=sample_id,
        sample_name=payload.get("sample_name"),
        experiment_item=payload.get("experiment_item"),
        current_location=payload.get("current_location"),
        note=payload.get("note"),
    )

    await db.commit()
    return updated_sample


async def _validate_sample_action_permission(
    current_user: dict,
    sample: dict,
    action: str,
) -> None:
    can_operate = can_manage_sample(current_user, sample)
    can_pickup = action == "pickup_confirmed" and can_confirm_pickup(current_user, sample)

    if not can_operate and not can_pickup:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to operate this sample",
        )

    if is_factory_role(current_user.get("role")) and action != "pickup_confirmed":
        raise HTTPException(
            status_code=403,
            detail="廠區使用者只能在待取件狀態確認取件",
        )


def _get_operator_name(payload: dict, current_user: dict) -> str:
    operator_name = payload.get("operator_name") or current_user.get("name")

    if not operator_name:
        raise HTTPException(
            status_code=400,
            detail="operator_name is required",
        )

    return operator_name


async def _receive_sample(
    db: AsyncSession,
    *,
    sample: dict,
    sample_id: str,
    payload: dict,
    current_lab: str | None,
    operator_name: str,
):
    if sample["status"] not in ("pending_receive", "transferring"):
        raise HTTPException(
            status_code=400,
            detail="只有待收樣或交接中的樣品可以確認收樣",
        )

    transfer_for_receive_data = await transfer_repo.get_transferring_sample_transfer_for_receive(
        db,
        sample_id=sample_id,
        current_lab=current_lab,
    )

    next_location = normalize_location_for_action(
        payload.get("current_location"),
        current_lab,
        "實驗暫存區",
    )

    updated_sample = await sample_repo.update_sample_as_received(
        db,
        sample_id=sample_id,
        next_location=next_location,
        operator_name=operator_name,
    )

    await sample_repo.update_current_lab_wips_location(
        db,
        sample_id=sample_id,
        current_lab=current_lab,
        next_location=next_location,
    )

    await transfer_repo.mark_sample_transfer_as_received(
        db,
        sample_id=sample_id,
        current_lab=current_lab,
        operator_name=operator_name,
    )

    await sample_repo.create_sample_history(
        db,
        sample_id=sample_id,
        action="receive",
        from_status=sample["status"],
        to_status="received",
        description=f"確認收樣，樣品移至 {next_location}",
        operator_name=operator_name,
        lab_name=current_lab,
    )

    if transfer_for_receive_data is not None:
        from_lab = transfer_for_receive_data.get("from_lab")
        to_lab = transfer_for_receive_data.get("to_lab")
        transfer_no = transfer_for_receive_data.get("transfer_no")

        if from_lab and from_lab != current_lab:
            await sample_repo.create_sample_history(
                db,
                sample_id=sample_id,
                action="transfer_received_by_next_lab",
                from_status=sample["status"],
                to_status="received",
                description=(
                    f"交接單 {transfer_no} 已由 {to_lab} 確認收樣，"
                    f"樣品已送達對方實驗室"
                ),
                operator_name=operator_name,
                lab_name=from_lab,
            )

    await db.commit()
    return updated_sample


async def _inbound_sample(
    db: AsyncSession,
    *,
    sample: dict,
    sample_id: str,
    payload: dict,
    current_lab: str | None,
    operator_name: str,
):
    storage_location_id = payload.get("storage_location_id")

    if storage_location_id:
        validate_uuid(storage_location_id, "storage_location_id")

    updated_sample = await sample_repo.update_sample_as_in_storage(
        db,
        sample_id=sample_id,
        current_location=payload.get("current_location"),
        storage_location_id=storage_location_id,
    )

    await sample_repo.create_sample_history(
        db,
        sample_id=sample_id,
        action="inbound",
        from_status=sample["status"],
        to_status="in_storage",
        description="樣品入庫",
        operator_name=operator_name,
        lab_name=current_lab,
    )

    await db.commit()
    return updated_sample


async def _outbound_sample(
    db: AsyncSession,
    *,
    sample: dict,
    sample_id: str,
    payload: dict,
    current_lab: str | None,
    operator_name: str,
):
    if sample["status"] not in ("split", "pending_transfer"):
        raise HTTPException(
            status_code=400,
            detail="只有已建立 WIP / 已分貨的樣品可以通知取件",
        )

    pending_transfer = await transfer_repo.get_active_sample_transfer_summary(
        db,
        sample_id,
    )

    if pending_transfer is not None:
        raise HTTPException(
            status_code=400,
            detail=(
                "此樣品仍有尚未完成的交接流程，不能通知取件："
                f"{pending_transfer.get('transfer_no')} "
                f"{pending_transfer.get('from_lab')} → "
                f"{pending_transfer.get('to_lab')} "
                f"({pending_transfer.get('status')})"
            ),
        )

    incomplete_wips = await sample_repo.list_incomplete_wips_for_sample(
        db,
        sample_id=sample_id,
    )

    if incomplete_wips:
        items = [
            f"{wip['lab_name']} / {wip['experiment_item']}：{wip['status']}"
            for wip in incomplete_wips
        ]

        raise HTTPException(
            status_code=400,
            detail=f"此樣品仍有未完成的 WIP，不能通知取件：{'、'.join(items)}",
        )

    completed_wips = await sample_repo.list_completed_wips_for_sample(
        db,
        sample_id=sample_id,
    )

    next_unfinished_experiment = None
    for experiment in parse_requested_experiments(sample.get("experiment_item")):
        completed = any(
            normalize_flow_value(wip["lab_name"])
            == normalize_flow_value(experiment["lab_name"])
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

    if payload.get("confirm_notify_pickup") not in (True, "true", "1", 1):
        raise HTTPException(
            status_code=400,
            detail="通知取件必須由使用者明確確認",
        )

    next_location = normalize_location_for_action(
        payload.get("current_location"),
        current_lab,
        "待取件區",
    )

    updated_sample = await sample_repo.update_sample_as_outbound(
        db,
        sample_id=sample_id,
        next_location=next_location,
        note=payload.get("note"),
    )

    await sample_repo.update_all_wips_location(
        db,
        sample_id=sample_id,
        next_location=next_location,
    )

    await sample_repo.create_sample_history(
        db,
        sample_id=sample_id,
        action="outbound",
        from_status=sample["status"],
        to_status="outbound",
        description=f"通知原使用者取件，樣品移至 {next_location}",
        operator_name=operator_name,
        lab_name=current_lab,
    )

    await db.commit()
    return updated_sample


async def _confirm_pickup_sample(
    db: AsyncSession,
    *,
    sample: dict,
    sample_id: str,
    payload: dict,
    operator_name: str,
):
    if sample["status"] != "outbound":
        raise HTTPException(
            status_code=400,
            detail="只有待取件 outbound 狀態可以確認取件",
        )

    pickup_lab = get_lab_from_location(sample.get("current_location"))
    next_location = payload.get("current_location") or "已由使用者取回"

    updated_sample = await sample_repo.update_sample_as_picked_up(
        db,
        sample_id=sample_id,
        next_location=next_location,
        operator_name=operator_name,
    )

    await sample_repo.update_all_wips_location(
        db,
        sample_id=sample_id,
        next_location=next_location,
    )

    await sample_repo.create_sample_history(
        db,
        sample_id=sample_id,
        action="pickup_confirmed",
        from_status=sample["status"],
        to_status="picked_up",
        description="廠區確認取件，樣品已由使用者取回",
        operator_name=operator_name,
        lab_name=pickup_lab,
    )

    await db.commit()
    return updated_sample


async def _split_sample(
    db: AsyncSession,
    *,
    sample: dict,
    sample_id: str,
    payload: dict,
    current_lab: str | None,
    operator_name: str,
):
    wips = payload.get("wips")

    if not isinstance(wips, list) or len(wips) == 0:
        raise HTTPException(
            status_code=400,
            detail="wips must be a non-empty list when action is split",
        )

    validated_wip_items = []

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

        validated_wip_items.append(
            {
                "lab_name": lab_name,
                "experiment_item": experiment_item,
            }
        )

    existing_sample_wips = await sample_repo.list_sample_wips_in_flow_order(
        db,
        sample_id=sample_id,
    )
    validate_wip_create_items_in_order(
        sample=sample,
        existing_wips=existing_sample_wips,
        requested_items=validated_wip_items,
    )

    next_location = normalize_location_for_action(
        payload.get("current_location"),
        current_lab,
        "實驗暫存區",
    )

    created_wips = []

    await sample_repo.update_sample_as_split(
        db,
        sample_id=sample_id,
        next_location=next_location,
    )

    await sample_repo.create_sample_history(
        db,
        sample_id=sample_id,
        action="split",
        from_status=sample["status"],
        to_status="split",
        description=f"樣品分貨並建立 WIP，樣品位於 {next_location}",
        operator_name=operator_name,
        lab_name=current_lab,
    )

    for item in wips:
        lab_name = item.get("lab_name")
        experiment_item = item.get("experiment_item")

        existing_wip = await sample_repo.get_existing_wip(
            db,
            sample_id=sample_id,
            lab_name=lab_name,
            experiment_item=experiment_item,
        )

        if existing_wip is not None:
            created_wips.append(existing_wip)
            continue

        wip_no = await generate_unique_wip_no(
            db=db,
            sample=sample,
            lab_name=lab_name,
            preferred_wip_no=item.get("wip_no"),
        )

        created_wip = await sample_repo.create_wip_from_split(
            db,
            wip_no=wip_no,
            sample_id=sample_id,
            order_no=sample.get("order_no"),
            lab_name=lab_name,
            experiment_item=experiment_item,
            priority=item.get("priority", "normal"),
            current_location=item.get("current_location") or next_location,
            note=item.get("note"),
        )
        created_wips.append(created_wip)

        await sample_repo.create_wip_history(
            db,
            wip_id=created_wip["id"],
            action="created_from_split",
            from_status=None,
            to_status="created",
            description=(
                f"由樣品 {sample['sample_no']} 分貨建立 WIP："
                f"{lab_name} / {experiment_item}，位置：{next_location}"
            ),
            operator_name=operator_name,
        )

    await db.commit()

    return {
        "message": "Sample split successfully",
        "sample_id": sample_id,
        "current_location": next_location,
        "created_wips": created_wips,
    }


async def handle_sample_action(
    db: AsyncSession,
    current_user: dict,
    sample_id: str,
    payload: dict,
):
    sample = await get_sample_or_404(sample_id, db)
    current_lab = get_user_lab(current_user)
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

    await _validate_sample_action_permission(current_user, sample, action)
    operator_name = _get_operator_name(payload, current_user)

    if action == "receive":
        return await _receive_sample(
            db,
            sample=sample,
            sample_id=sample_id,
            payload=payload,
            current_lab=current_lab,
            operator_name=operator_name,
        )

    if action == "inbound":
        return await _inbound_sample(
            db,
            sample=sample,
            sample_id=sample_id,
            payload=payload,
            current_lab=current_lab,
            operator_name=operator_name,
        )

    if action == "outbound":
        return await _outbound_sample(
            db,
            sample=sample,
            sample_id=sample_id,
            payload=payload,
            current_lab=current_lab,
            operator_name=operator_name,
        )

    if action == "pickup_confirmed":
        return await _confirm_pickup_sample(
            db,
            sample=sample,
            sample_id=sample_id,
            payload=payload,
            operator_name=operator_name,
        )

    if action == "split":
        return await _split_sample(
            db,
            sample=sample,
            sample_id=sample_id,
            payload=payload,
            current_lab=current_lab,
            operator_name=operator_name,
        )

    raise HTTPException(status_code=400, detail="Unsupported action")
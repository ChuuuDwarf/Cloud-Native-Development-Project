"""Transfers service layer.

Route 只呼叫這層；SQL 集中放在 app/repos/transfer_repo.py。
"""

from uuid import UUID

from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.repos import transfer_repo

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
        from app.services.workflow_helpers import resolve_current_user

        return await resolve_current_user(db, request)
    except Exception:
        await db.rollback()
        return fallback_user


def get_user_lab(user: dict):
    return user.get("lab_name") or user.get("department")


def lab_location(lab_name: str | None, area: str):
    if not lab_name:
        return area

    lab_name = lab_name.strip()

    if lab_name.endswith(area):
        return lab_name

    return f"{lab_name} {area}"


def receive_location(lab_name: str | None):
    return lab_location(lab_name, "收樣區")


def transfer_waiting_location(lab_name: str | None):
    return lab_location(lab_name, "交接待送區")


def build_transfer_visibility_filter(current_user: dict):
    role = current_user.get("role")
    where_clauses: list[str] = []
    params: dict[str, object] = {}

    if role == "system_admin":
        return where_clauses, params

    if role in ("lab_engineer", "lab_supervisor"):
        current_lab = get_user_lab(current_user)

        if not current_lab:
            where_clauses.append("1 = 0")
            return where_clauses, params

        where_clauses.append("(from_lab = :current_lab OR to_lab = :current_lab)")
        params["current_lab"] = current_lab
        return where_clauses, params

    if role == "plant_user":
        where_clauses.append("1 = 0")
        return where_clauses, params

    where_clauses.append("1 = 0")
    return where_clauses, params


def validate_uuid(value: str | None, field_name: str) -> None:
    try:
        UUID(str(value))
    except (TypeError, ValueError) as err:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must be a valid UUID",
        ) from err


async def generate_transfer_no(db: AsyncSession):
    total = await transfer_repo.count_transfers(db)

    for index in range(total + 1, total + 1000):
        transfer_no = f"TRF-2026-{index:04d}"

        if not await transfer_repo.transfer_no_exists(db, transfer_no):
            return transfer_no

    raise HTTPException(status_code=500, detail="Unable to generate transfer_no")


async def get_transfer_or_404(transfer_id: str, db: AsyncSession):
    validate_uuid(transfer_id, "transfer_id")

    transfer = await transfer_repo.get_transfer_by_id(db, transfer_id)

    if transfer is None:
        raise HTTPException(status_code=404, detail="Transfer not found")

    return transfer


async def get_sample_or_404(sample_id: str, db: AsyncSession):
    validate_uuid(sample_id, "sample_id")

    sample = await transfer_repo.get_sample_by_id(db, sample_id)

    if sample is None:
        raise HTTPException(status_code=404, detail="Sample not found")

    return sample


async def get_wip_or_404(wip_id: str, db: AsyncSession):
    validate_uuid(wip_id, "wip_id")

    wip = await transfer_repo.get_wip_by_id(db, wip_id)

    if wip is None:
        raise HTTPException(status_code=404, detail="WIP not found")

    return wip


async def create_pending_sample_transfer_if_missing(
    db: AsyncSession,
    sample: dict,
    from_lab: str,
    to_lab: str,
    handed_by: str | None,
    note: str | None = None,
) -> dict | None:
    existing = await transfer_repo.get_pending_sample_transfer(
        db,
        sample_id=sample["id"],
        from_lab=from_lab,
        to_lab=to_lab,
    )

    if existing is not None:
        return existing

    return await transfer_repo.create_pending_sample_transfer(
        db,
        transfer_no=await generate_transfer_no(db),
        sample_id=sample["id"],
        order_no=sample.get("order_no"),
        sample_no=sample.get("sample_no"),
        from_lab=from_lab,
        to_lab=to_lab,
        handed_by=handed_by,
        note=note,
    )


async def list_transfers(
    db: AsyncSession,
    current_user: dict,
):
    where_clauses, params = build_transfer_visibility_filter(current_user)

    return await transfer_repo.list_transfers(
        db,
        where_clauses=where_clauses,
        params=params,
    )


async def create_transfer(
    db: AsyncSession,
    current_user: dict,
    payload: dict,
):
    if current_user.get("role") == "plant_user":
        raise HTTPException(
            status_code=403,
            detail="廠區使用者不能建立交接單",
        )

    target_type = payload.get("target_type")
    target_id = payload.get("target_id")

    if target_type not in ("sample", "wip"):
        raise HTTPException(
            status_code=400,
            detail="target_type must be either 'sample' or 'wip'",
        )

    validate_uuid(target_id, "target_id")
    target_id = str(target_id)

    from_lab = payload.get("from_lab") or get_user_lab(current_user)
    to_lab = payload.get("to_lab")
    handed_by = payload.get("handed_by") or current_user.get("name")

    if not from_lab:
        raise HTTPException(status_code=400, detail="from_lab is required")

    if not to_lab:
        raise HTTPException(status_code=400, detail="to_lab is required")

    if not handed_by:
        raise HTTPException(status_code=400, detail="handed_by is required")

    if from_lab == to_lab:
        raise HTTPException(
            status_code=400,
            detail="from_lab and to_lab cannot be the same",
        )

    current_lab = get_user_lab(current_user)

    if (current_user.get("role") in ("lab_engineer", "lab_supervisor")) and current_lab != from_lab:
        raise HTTPException(
            status_code=403,
            detail="只能從自己所屬實驗室建立交接單",
        )

    if target_type == "sample":
        sample = await get_sample_or_404(target_id, db)
        order_no = payload.get("order_no") or sample.get("order_no")
        sample_no = payload.get("sample_no") or sample.get("sample_no")
        wip_no = payload.get("wip_no")
        current_status = sample.get("status")

        if current_user.get("role") in ("lab_engineer", "lab_supervisor"):
            sample_location = sample.get("current_location") or ""
            if current_lab and not sample_location.startswith(current_lab):
                raise HTTPException(
                    status_code=403,
                    detail="只能交接目前位於自己實驗室的樣品",
                )

    else:
        wip = await get_wip_or_404(target_id, db)
        order_no = payload.get("order_no") or wip.get("order_no")
        sample_no = payload.get("sample_no")
        wip_no = payload.get("wip_no") or wip.get("wip_no")
        current_status = wip.get("status")

        if current_user.get("role") in ("lab_engineer", "lab_supervisor"):
            wip_location = wip.get("current_location") or ""
            if current_lab and not wip_location.startswith(current_lab):
                raise HTTPException(
                    status_code=403,
                    detail="只能交接目前位於自己實驗室的 WIP",
                )

    existing = await transfer_repo.get_active_transfer_for_target(
        db,
        target_type=target_type,
        target_id=target_id,
    )

    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="這個樣品或 WIP 已經有尚未完成的交接申請",
        )

    transfer = await transfer_repo.create_transfer(
        db,
        transfer_no=payload.get("transfer_no") or await generate_transfer_no(db),
        target_type=target_type,
        target_id=target_id,
        order_no=order_no,
        sample_no=sample_no,
        wip_no=wip_no,
        from_lab=from_lab,
        to_lab=to_lab,
        handed_by=handed_by,
        note=payload.get("note"),
    )

    waiting_location = transfer_waiting_location(from_lab)

    if target_type == "sample":
        await transfer_repo.update_sample_location(
            db,
            sample_id=target_id,
            location=waiting_location,
        )

        await transfer_repo.update_next_lab_wips_location(
            db,
            sample_id=target_id,
            to_lab=to_lab,
            next_location=waiting_location,
        )

        await transfer_repo.create_sample_history(
            db,
            sample_id=target_id,
            action="transfer_created",
            from_status=current_status,
            to_status=current_status,
            description=f"建立交接申請：{from_lab} → {to_lab}，樣品移至 {waiting_location}",
            operator_name=handed_by,
            lab_name=from_lab,
        )

    if target_type == "wip":
        await transfer_repo.update_wip_location(
            db,
            wip_id=target_id,
            location=waiting_location,
        )

        await transfer_repo.create_wip_history(
            db,
            wip_id=target_id,
            action="transfer_created",
            from_status=current_status,
            to_status=current_status,
            description=f"建立交接申請：{from_lab} → {to_lab}，WIP 移至 {waiting_location}",
            operator_name=handed_by,
        )

    await db.commit()

    return transfer


async def handle_transfer_action(
    db: AsyncSession,
    current_user: dict,
    transfer_id: str,
    payload: dict,
):
    if current_user.get("role") == "plant_user":
        raise HTTPException(
            status_code=403,
            detail="廠區使用者不能操作交接單",
        )

    current_lab = get_user_lab(current_user)
    transfer_data = await get_transfer_or_404(transfer_id, db)

    action = payload.get("action")

    if action not in ("send", "cancel"):
        raise HTTPException(
            status_code=400,
            detail="action must be one of: send, cancel",
        )

    operator_name = payload.get("operator_name") or current_user.get("name")

    if not operator_name:
        raise HTTPException(status_code=400, detail="operator_name is required")

    if current_user.get("role") in ("lab_engineer", "lab_supervisor") and (
        current_lab
        and transfer_data.get("from_lab")
        and current_lab != transfer_data.get("from_lab")
    ):
        raise HTTPException(
            status_code=403,
            detail="只有來源實驗室可以操作這筆交接單",
        )

    if action == "send":
        return await send_transfer(
            db=db,
            transfer_id=transfer_id,
            transfer_data=transfer_data,
            operator_name=operator_name,
        )

    if action == "cancel":
        return await cancel_transfer(
            db=db,
            transfer_id=transfer_id,
            transfer_data=transfer_data,
            operator_name=operator_name,
        )

    raise HTTPException(status_code=400, detail="Unsupported action")


async def send_transfer(
    db: AsyncSession,
    transfer_id: str,
    transfer_data: dict,
    operator_name: str,
):
    if transfer_data["status"] != "pending":
        raise HTTPException(
            status_code=400,
            detail="只有 pending 狀態可以送出交接",
        )

    to_lab = transfer_data.get("to_lab")
    next_location = receive_location(to_lab)

    if not to_lab:
        raise HTTPException(
            status_code=400,
            detail="to_lab is required before sending transfer",
        )

    await transfer_repo.mark_transfer_as_transferring(db, transfer_id)

    if transfer_data["target_type"] == "sample":
        sample = await get_sample_or_404(transfer_data["target_id"], db)

        await transfer_repo.mark_sample_as_pending_receive(
            db,
            sample_id=transfer_data["target_id"],
            next_location=next_location,
        )

        await transfer_repo.update_next_lab_wips_location(
            db,
            sample_id=transfer_data["target_id"],
            to_lab=to_lab,
            next_location=next_location,
        )

        await transfer_repo.create_sample_history(
            db,
            sample_id=transfer_data["target_id"],
            action="transfer_sent_to_next_lab_receive_area",
            from_status=sample.get("status"),
            to_status="pending_receive",
            description=(
                f"送出交接單 {transfer_data.get('transfer_no')}："
                f"{transfer_data.get('from_lab')} → {transfer_data.get('to_lab')}，"
                f"樣品移至 {next_location}，等待接收實驗室收樣；"
                "此步驟不是使用者取件"
            ),
            operator_name=operator_name,
            lab_name=transfer_data.get("from_lab"),
        )

    if transfer_data["target_type"] == "wip":
        wip = await get_wip_or_404(transfer_data["target_id"], db)

        await transfer_repo.update_wip_location(
            db,
            wip_id=transfer_data["target_id"],
            location=next_location,
        )

        await transfer_repo.create_wip_history(
            db,
            wip_id=transfer_data["target_id"],
            action="transfer_sent_to_next_lab_receive_area",
            from_status=wip.get("status"),
            to_status=wip.get("status"),
            description=(
                f"送出交接單 {transfer_data.get('transfer_no')}："
                f"{transfer_data.get('from_lab')} → {transfer_data.get('to_lab')}，"
                f"WIP 移至 {next_location}"
            ),
            operator_name=operator_name,
        )

    await db.commit()

    return {
        "message": "Transfer sent successfully. Sample moved to next lab receive area.",
        "next_location": next_location,
        "status": "transferring",
    }


async def cancel_transfer(
    db: AsyncSession,
    transfer_id: str,
    transfer_data: dict,
    operator_name: str,
):
    if transfer_data["status"] != "pending":
        raise HTTPException(
            status_code=400,
            detail="只有 pending 狀態可以取消",
        )

    await transfer_repo.cancel_transfer(db, transfer_id)

    if transfer_data["target_type"] == "sample":
        sample = await get_sample_or_404(transfer_data["target_id"], db)
        fallback_location = transfer_waiting_location(transfer_data.get("from_lab"))

        await transfer_repo.update_sample_location(
            db,
            sample_id=transfer_data["target_id"],
            location=fallback_location,
        )

        await transfer_repo.create_sample_history(
            db,
            sample_id=transfer_data["target_id"],
            action="transfer_cancelled",
            from_status=sample.get("status"),
            to_status=sample.get("status"),
            description=f"取消交接單 {transfer_data.get('transfer_no')}",
            operator_name=operator_name,
            lab_name=transfer_data.get("from_lab"),
        )

    if transfer_data["target_type"] == "wip":
        wip = await get_wip_or_404(transfer_data["target_id"], db)

        await transfer_repo.create_wip_history(
            db,
            wip_id=transfer_data["target_id"],
            action="transfer_cancelled",
            from_status=wip.get("status"),
            to_status=wip.get("status"),
            description=f"取消交接單 {transfer_data.get('transfer_no')}",
            operator_name=operator_name,
        )

    await db.commit()

    return {"message": "Transfer cancelled successfully"}

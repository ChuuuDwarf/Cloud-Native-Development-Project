from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

router = APIRouter(
    prefix="/api/transfers",
    tags=["transfers"],
)


# 這個 route 檔現在只保留 API endpoint 與 request/response 組裝。
# 權限、位置、ID、狀態流轉等 helper 已拆到 service 檔，方便後續維護與測試。
from app.services.transfer_service import *  # noqa: F403 - route endpoint 會使用拆出的 helper

@router.get("")
async def get_transfers(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    current_user = await get_active_user(db, request)
    where_clauses, params = build_transfer_visibility_filter(current_user)

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    result = await db.execute(
        text(
            f"""
            SELECT
                id,
                transfer_no,
                target_type,
                target_id,
                order_no,
                sample_no,
                wip_no,
                from_lab,
                to_lab,
                handed_by,
                received_by,
                status,
                transferred_at,
                received_at,
                note,
                created_at,
                updated_at
            FROM transfers
            {where_sql}
            ORDER BY created_at DESC
            """
        ),
        params,
    )

    return [dict(row._mapping) for row in result]


# TODO(integration): 建立交接單目前在本 route 寫入 transfers。
# 正式整合樣品流轉/倉儲模組後，可考慮改由 transfer service 統一處理通知與簽收流程。
@router.post("")
async def create_transfer(
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    current_user = await get_active_user(db, request)

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

    if current_user.get("role") in ("lab_engineer", "lab_supervisor"):
        if current_lab != from_lab:
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

    existing_result = await db.execute(
        text(
            """
            SELECT *
            FROM transfers
            WHERE target_type = :target_type
              AND target_id = :target_id
              AND status IN ('pending', 'transferring')
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {
            "target_type": target_type,
            "target_id": target_id,
        },
    )
    existing = existing_result.fetchone()

    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="這個樣品或 WIP 已經有尚未完成的交接申請",
        )

    result = await db.execute(
        text(
            """
            INSERT INTO transfers (
                transfer_no,
                target_type,
                target_id,
                order_no,
                sample_no,
                wip_no,
                from_lab,
                to_lab,
                handed_by,
                status,
                note
            )
            VALUES (
                :transfer_no,
                :target_type,
                :target_id,
                :order_no,
                :sample_no,
                :wip_no,
                :from_lab,
                :to_lab,
                :handed_by,
                'pending',
                :note
            )
            RETURNING *
            """
        ),
        {
            "transfer_no": payload.get("transfer_no") or await generate_transfer_no(db),
            "target_type": target_type,
            "target_id": target_id,
            "order_no": order_no,
            "sample_no": sample_no,
            "wip_no": wip_no,
            "from_lab": from_lab,
            "to_lab": to_lab,
            "handed_by": handed_by,
            "note": payload.get("note"),
        },
    )

    transfer = dict(result.fetchone()._mapping)
    waiting_location = transfer_waiting_location(from_lab)

    if target_type == "sample":
        await db.execute(
            text(
                """
                UPDATE samples
                SET
                    current_location = :waiting_location,
                    updated_at = NOW()
                WHERE id = :sample_id
                """
            ),
            {
                "sample_id": target_id,
                "waiting_location": waiting_location,
            },
        )

        await update_next_lab_wips_location(
            db=db,
            sample_id=target_id,
            to_lab=to_lab,
            next_location=waiting_location,
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
                    'transfer_created',
                    :from_status,
                    :to_status,
                    :description,
                    :operator_name,
                    :lab_name
                )
                """
            ),
            {
                "sample_id": target_id,
                "from_status": current_status,
                "to_status": current_status,
                "description": f"建立交接申請：{from_lab} → {to_lab}，樣品移至 {waiting_location}",
                "operator_name": handed_by,
                "lab_name": from_lab,
            },
        )

    if target_type == "wip":
        await db.execute(
            text(
                """
                UPDATE wips
                SET
                    current_location = :waiting_location,
                    updated_at = NOW()
                WHERE id = :wip_id
                """
            ),
            {
                "wip_id": target_id,
                "waiting_location": waiting_location,
            },
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
                    'transfer_created',
                    :from_status,
                    :to_status,
                    :description,
                    :operator_name
                )
                """
            ),
            {
                "wip_id": target_id,
                "from_status": current_status,
                "to_status": current_status,
                "description": f"建立交接申請：{from_lab} → {to_lab}，WIP 移至 {waiting_location}",
                "operator_name": handed_by,
            },
        )

    await db.commit()

    return transfer


# TODO(integration): 交接確認目前直接更新 transfer/sample/wip 狀態。
# 正式模組合併後，請確認是否需同步 storage/order/schedule/warn 模組事件。
@router.post("/{transfer_id}/actions")
async def transfer_action(
    transfer_id: str,
    payload: dict,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    current_user = await get_active_user(db, request)

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

    if current_user.get("role") in ("lab_engineer", "lab_supervisor"):
        if (
            current_lab
            and transfer_data.get("from_lab")
            and current_lab != transfer_data.get("from_lab")
        ):
            raise HTTPException(
                status_code=403,
                detail="只有來源實驗室可以操作這筆交接單",
            )

    if action == "send":
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

        await db.execute(
            text(
                """
                UPDATE transfers
                SET
                    status = 'transferring',
                    transferred_at = NOW(),
                    updated_at = NOW()
                WHERE id = :transfer_id
                """
            ),
            {"transfer_id": transfer_id},
        )

        if transfer_data["target_type"] == "sample":
            sample = await get_sample_or_404(transfer_data["target_id"], db)

            await db.execute(
                text(
                    """
                    UPDATE samples
                    SET
                        status = 'pending_receive',
                        current_location = :next_location,
                        updated_at = NOW()
                    WHERE id = :sample_id
                    """
                ),
                {
                    "sample_id": transfer_data["target_id"],
                    "next_location": next_location,
                },
            )

            await update_next_lab_wips_location(
                db=db,
                sample_id=transfer_data["target_id"],
                to_lab=to_lab,
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
                        'transfer_sent_to_next_lab_receive_area',
                        :from_status,
                        'pending_receive',
                        :description,
                        :operator_name,
                        :lab_name
                    )
                    """
                ),
                {
                    "sample_id": transfer_data["target_id"],
                    "from_status": sample.get("status"),
                    "description": (
                        f"送出交接單 {transfer_data.get('transfer_no')}："
                        f"{transfer_data.get('from_lab')} → {transfer_data.get('to_lab')}，"
                        f"樣品移至 {next_location}"
                    ),
                    "operator_name": operator_name,
                    "lab_name": transfer_data.get("from_lab"),
                },
            )

        if transfer_data["target_type"] == "wip":
            wip = await get_wip_or_404(transfer_data["target_id"], db)

            await db.execute(
                text(
                    """
                    UPDATE wips
                    SET
                        current_location = :next_location,
                        updated_at = NOW()
                    WHERE id = :wip_id
                    """
                ),
                {
                    "wip_id": transfer_data["target_id"],
                    "next_location": next_location,
                },
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
                        'transfer_sent_to_next_lab_receive_area',
                        :from_status,
                        :to_status,
                        :description,
                        :operator_name
                    )
                    """
                ),
                {
                    "wip_id": transfer_data["target_id"],
                    "from_status": wip.get("status"),
                    "to_status": wip.get("status"),
                    "description": (
                        f"送出交接單 {transfer_data.get('transfer_no')}："
                        f"{transfer_data.get('from_lab')} → {transfer_data.get('to_lab')}，"
                        f"WIP 移至 {next_location}"
                    ),
                    "operator_name": operator_name,
                },
            )

        await db.commit()

        return {
            "message": "Transfer sent successfully. Sample moved to next lab receive area.",
            "next_location": next_location,
            "status": "transferring",
        }

    if action == "cancel":
        if transfer_data["status"] != "pending":
            raise HTTPException(
                status_code=400,
                detail="只有 pending 狀態可以取消",
            )

        await db.execute(
            text(
                """
                UPDATE transfers
                SET
                    status = 'cancelled',
                    updated_at = NOW()
                WHERE id = :transfer_id
                """
            ),
            {"transfer_id": transfer_id},
        )

        if transfer_data["target_type"] == "sample":
            sample = await get_sample_or_404(transfer_data["target_id"], db)
            fallback_location = transfer_waiting_location(transfer_data.get("from_lab"))

            await db.execute(
                text(
                    """
                    UPDATE samples
                    SET
                        current_location = :fallback_location,
                        updated_at = NOW()
                    WHERE id = :sample_id
                    """
                ),
                {
                    "sample_id": transfer_data["target_id"],
                    "fallback_location": fallback_location,
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
                        'transfer_cancelled',
                        :from_status,
                        :to_status,
                        :description,
                        :operator_name,
                        :lab_name
                    )
                    """
                ),
                {
                    "sample_id": transfer_data["target_id"],
                    "from_status": sample.get("status"),
                    "to_status": sample.get("status"),
                    "description": f"取消交接單 {transfer_data.get('transfer_no')}",
                    "operator_name": operator_name,
                    "lab_name": transfer_data.get("from_lab"),
                },
            )

        if transfer_data["target_type"] == "wip":
            wip = await get_wip_or_404(transfer_data["target_id"], db)

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
                        'transfer_cancelled',
                        :from_status,
                        :to_status,
                        :description,
                        :operator_name
                    )
                    """
                ),
                {
                    "wip_id": transfer_data["target_id"],
                    "from_status": wip.get("status"),
                    "to_status": wip.get("status"),
                    "description": f"取消交接單 {transfer_data.get('transfer_no')}",
                    "operator_name": operator_name,
                },
            )

        await db.commit()

        return {"message": "Transfer cancelled successfully"}

    raise HTTPException(status_code=400, detail="Unsupported action")

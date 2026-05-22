from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db

router = APIRouter(
    prefix="/api/transfers",
    tags=["transfers"],
)


fallback_user = {
    "id": "fallback",
    "name": "張志明",
    "role": "lab_staff",
    "role_name": "實驗室人員",
    "department": "Lab A",
    "lab_name": "Lab A",
    "email": "",
}


def get_active_user(request: Request | None = None):
    try:
        from app.routes.others import resolve_current_user

        return resolve_current_user(request)
    except Exception:
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
    where_clauses = []
    params = {}

    if role == "system_admin":
        return where_clauses, params

    if role in ("lab_staff", "lab_supervisor"):
        current_lab = get_user_lab(current_user)

        if not current_lab:
            where_clauses.append("1 = 0")
            return where_clauses, params

        where_clauses.append("from_lab = :current_lab")
        params["current_lab"] = current_lab
        return where_clauses, params

    if role == "factory_user":
        where_clauses.append("1 = 0")
        return where_clauses, params

    where_clauses.append("1 = 0")
    return where_clauses, params


def validate_uuid(value: str | None, field_name: str) -> None:
    try:
        UUID(str(value))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must be a valid UUID",
        )


def generate_transfer_no(db: Session):
    result = db.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM transfers
            """
        )
    )

    total = int(result.fetchone()._mapping["total"])

    for index in range(total + 1, total + 1000):
        transfer_no = f"TRF-2026-{index:04d}"

        exists = db.execute(
            text(
                """
                SELECT 1
                FROM transfers
                WHERE transfer_no = :transfer_no
                LIMIT 1
                """
            ),
            {"transfer_no": transfer_no},
        ).fetchone()

        if exists is None:
            return transfer_no

    raise HTTPException(status_code=500, detail="Unable to generate transfer_no")


def get_transfer_or_404(transfer_id: str, db: Session):
    validate_uuid(transfer_id, "transfer_id")

    result = db.execute(
        text(
            """
            SELECT *
            FROM transfers
            WHERE id = :transfer_id
            """
        ),
        {"transfer_id": transfer_id},
    )

    transfer = result.fetchone()

    if transfer is None:
        raise HTTPException(status_code=404, detail="Transfer not found")

    return dict(transfer._mapping)


def get_sample_or_404(sample_id: str, db: Session):
    validate_uuid(sample_id, "sample_id")

    result = db.execute(
        text(
            """
            SELECT *
            FROM samples
            WHERE id = :sample_id
            """
        ),
        {"sample_id": sample_id},
    )

    sample = result.fetchone()

    if sample is None:
        raise HTTPException(status_code=404, detail="Sample not found")

    return dict(sample._mapping)


def get_wip_or_404(wip_id: str, db: Session):
    validate_uuid(wip_id, "wip_id")

    result = db.execute(
        text(
            """
            SELECT *
            FROM wips
            WHERE id = :wip_id
            """
        ),
        {"wip_id": wip_id},
    )

    wip = result.fetchone()

    if wip is None:
        raise HTTPException(status_code=404, detail="WIP not found")

    return dict(wip._mapping)


def update_next_lab_wips_location(
    db: Session,
    sample_id: str,
    to_lab: str | None,
    next_location: str,
):
    if not to_lab:
        return

    db.execute(
        text(
            """
            UPDATE wips
            SET
                current_location = :next_location,
                updated_at = NOW()
            WHERE sample_id = :sample_id
              AND lab_name = :to_lab
              AND status <> 'completed'
            """
        ),
        {
            "sample_id": sample_id,
            "to_lab": to_lab,
            "next_location": next_location,
        },
    )


@router.get("")
def get_transfers(
    request: Request,
    db: Session = Depends(get_db),
):
    current_user = get_active_user(request)
    where_clauses, params = build_transfer_visibility_filter(current_user)

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    result = db.execute(
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


@router.post("")
def create_transfer(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
):
    current_user = get_active_user(request)

    if current_user.get("role") == "factory_user":
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

    if current_user.get("role") in ("lab_staff", "lab_supervisor"):
        if current_lab != from_lab:
            raise HTTPException(
                status_code=403,
                detail="只能從自己所屬實驗室建立交接單",
            )

    if target_type == "sample":
        sample = get_sample_or_404(target_id, db)
        order_no = payload.get("order_no") or sample.get("order_no")
        sample_no = payload.get("sample_no") or sample.get("sample_no")
        wip_no = payload.get("wip_no")
        current_status = sample.get("status")

        if current_user.get("role") in ("lab_staff", "lab_supervisor"):
            sample_location = sample.get("current_location") or ""
            if current_lab and not sample_location.startswith(current_lab):
                raise HTTPException(
                    status_code=403,
                    detail="只能交接目前位於自己實驗室的樣品",
                )

    else:
        wip = get_wip_or_404(target_id, db)
        order_no = payload.get("order_no") or wip.get("order_no")
        sample_no = payload.get("sample_no")
        wip_no = payload.get("wip_no") or wip.get("wip_no")
        current_status = wip.get("status")

        if current_user.get("role") in ("lab_staff", "lab_supervisor"):
            wip_location = wip.get("current_location") or ""
            if current_lab and not wip_location.startswith(current_lab):
                raise HTTPException(
                    status_code=403,
                    detail="只能交接目前位於自己實驗室的 WIP",
                )

    existing = db.execute(
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
    ).fetchone()

    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="這個樣品或 WIP 已經有尚未完成的交接申請",
        )

    result = db.execute(
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
            "transfer_no": payload.get("transfer_no") or generate_transfer_no(db),
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
        db.execute(
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

        update_next_lab_wips_location(
            db=db,
            sample_id=target_id,
            to_lab=to_lab,
            next_location=waiting_location,
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
        db.execute(
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

    db.commit()

    return transfer


@router.post("/{transfer_id}/actions")
def transfer_action(
    transfer_id: str,
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
):
    current_user = get_active_user(request)

    if current_user.get("role") == "factory_user":
        raise HTTPException(
            status_code=403,
            detail="廠區使用者不能操作交接單",
        )

    current_lab = get_user_lab(current_user)
    transfer_data = get_transfer_or_404(transfer_id, db)

    action = payload.get("action")

    if action not in ("send", "cancel"):
        raise HTTPException(
            status_code=400,
            detail="action must be one of: send, cancel",
        )

    operator_name = payload.get("operator_name") or current_user.get("name")

    if not operator_name:
        raise HTTPException(status_code=400, detail="operator_name is required")

    if current_user.get("role") in ("lab_staff", "lab_supervisor"):
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

        db.execute(
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
            sample = get_sample_or_404(transfer_data["target_id"], db)

            db.execute(
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

            update_next_lab_wips_location(
                db=db,
                sample_id=transfer_data["target_id"],
                to_lab=to_lab,
                next_location=next_location,
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
            wip = get_wip_or_404(transfer_data["target_id"], db)

            db.execute(
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

        db.commit()

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

        db.execute(
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
            sample = get_sample_or_404(transfer_data["target_id"], db)
            fallback_location = transfer_waiting_location(transfer_data.get("from_lab"))

            db.execute(
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
            wip = get_wip_or_404(transfer_data["target_id"], db)

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

        db.commit()

        return {"message": "Transfer cancelled successfully"}

    raise HTTPException(status_code=400, detail="Unsupported action")
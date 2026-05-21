from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db

router = APIRouter(
    prefix="/api/transfers",
    tags=["transfers"],
)


def validate_uuid(value: str | None, field_name: str) -> None:
    try:
        UUID(str(value))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must be a valid UUID",
        )


@router.get("")
def get_transfers(db: Session = Depends(get_db)):
    result = db.execute(
        text(
            """
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
            ORDER BY created_at DESC
            """
        )
    )

    return [dict(row._mapping) for row in result]


@router.post("")
def create_transfer(payload: dict, db: Session = Depends(get_db)):
    target_type = payload.get("target_type")
    target_id = payload.get("target_id")

    if target_type not in ("sample", "wip"):
        raise HTTPException(
            status_code=400,
            detail="target_type must be either 'sample' or 'wip'",
        )

    validate_uuid(target_id, "target_id")

    # TODO(auth):
    # handed_by 目前先由 request body 傳入文字，格式建議為「實驗室／姓名」。
    # 等 /api/me 完成後，改由登入者資訊自動帶入：
    # handed_by_user_id = current_user.id
    # handed_by_name = current_user.name
    # handed_by_lab = current_user.lab_name

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
            "transfer_no": payload.get("transfer_no"),
            "target_type": target_type,
            "target_id": target_id,
            "order_no": payload.get("order_no"),
            "sample_no": payload.get("sample_no"),
            "wip_no": payload.get("wip_no"),
            "from_lab": payload.get("from_lab"),
            "to_lab": payload.get("to_lab"),
            "handed_by": payload.get("handed_by"),
            "note": payload.get("note"),
        },
    )

    db.commit()

    return dict(result.fetchone()._mapping)


@router.post("/{transfer_id}/actions")
def transfer_action(
    transfer_id: str,
    payload: dict,
    db: Session = Depends(get_db),
):
    validate_uuid(transfer_id, "transfer_id")

    action = payload.get("action")

    if action not in ("send", "receive", "cancel"):
        raise HTTPException(
            status_code=400,
            detail="action must be one of: send, receive, cancel",
        )

    transfer_result = db.execute(
        text(
            """
            SELECT *
            FROM transfers
            WHERE id = :transfer_id
            """
        ),
        {"transfer_id": transfer_id},
    )

    transfer = transfer_result.fetchone()

    if transfer is None:
        raise HTTPException(status_code=404, detail="Transfer not found")

    transfer_data = dict(transfer._mapping)

    if action == "send":
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

        db.commit()

        return {"message": "Transfer sent successfully"}

    if action == "receive":
        received_by = payload.get("received_by")

        if not received_by:
            raise HTTPException(
                status_code=400,
                detail="received_by is required when action is receive",
            )

        # TODO(auth):
        # received_by 目前先由 request body 傳入文字，格式建議為「實驗室／姓名」。
        # 等 /api/me 完成後，改由登入者資訊自動帶入：
        # received_by_user_id = current_user.id
        # received_by_name = current_user.name
        # received_by_lab = current_user.lab_name

        db.execute(
            text(
                """
                UPDATE transfers
                SET
                    status = 'received',
                    received_by = :received_by,
                    received_at = NOW(),
                    updated_at = NOW()
                WHERE id = :transfer_id
                """
            ),
            {
                "transfer_id": transfer_id,
                "received_by": received_by,
            },
        )

        if transfer_data["target_type"] == "wip":
            db.execute(
                text(
                    """
                    UPDATE wips
                    SET
                        current_location = :to_lab,
                        updated_at = NOW()
                    WHERE id = :target_id
                    """
                ),
                {
                    "target_id": transfer_data["target_id"],
                    "to_lab": transfer_data["to_lab"],
                },
            )

            db.execute(
                text(
                    """
                    INSERT INTO wip_histories (
                        wip_id,
                        action,
                        description,
                        operator_name
                    )
                    VALUES (
                        :wip_id,
                        'transfer_received',
                        :description,
                        :operator_name
                    )
                    """
                ),
                {
                    "wip_id": transfer_data["target_id"],
                    "description": f"WIP 已交接至 {transfer_data['to_lab']}",
                    "operator_name": received_by,
                },
            )

        if transfer_data["target_type"] == "sample":
            db.execute(
                text(
                    """
                    UPDATE samples
                    SET
                        current_location = :to_lab,
                        updated_at = NOW()
                    WHERE id = :target_id
                    """
                ),
                {
                    "target_id": transfer_data["target_id"],
                    "to_lab": transfer_data["to_lab"],
                },
            )

            db.execute(
                text(
                    """
                    INSERT INTO sample_histories (
                        sample_id,
                        action,
                        description,
                        operator_name
                    )
                    VALUES (
                        :sample_id,
                        'transfer_received',
                        :description,
                        :operator_name
                    )
                    """
                ),
                {
                    "sample_id": transfer_data["target_id"],
                    "description": f"樣品已交接至 {transfer_data['to_lab']}",
                    "operator_name": received_by,
                },
            )

        db.commit()

        return {"message": "Transfer received successfully"}

    if action == "cancel":
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

        db.commit()

        return {"message": "Transfer cancelled successfully"}

    raise HTTPException(status_code=400, detail="Unsupported action")
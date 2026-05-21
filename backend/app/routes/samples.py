from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter(
    prefix="/api/samples",
    tags=["samples"],
)


def validate_uuid(value: str | None, field_name: str) -> None:
    try:
        UUID(str(value))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must be a valid UUID",
        )


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


@router.get("")
def get_samples(db: Session = Depends(get_db)):
    result = db.execute(
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
                storage_location_id,
                received_at,
                received_by,
                picked_up_at,
                picked_up_by,
                note,
                created_at,
                updated_at
            FROM samples
            ORDER BY created_at DESC
            """
        )
    )

    return [dict(row._mapping) for row in result]


@router.get("/{sample_id}")
def get_sample(sample_id: str, db: Session = Depends(get_db)):
    return get_sample_or_404(sample_id, db)


@router.get("/{sample_id}/history")
def get_sample_history(sample_id: str, db: Session = Depends(get_db)):
    get_sample_or_404(sample_id, db)

    result = db.execute(
        text(
            """
            SELECT
                id,
                sample_id,
                action,
                from_status,
                to_status,
                description,
                operator_name,
                created_at
            FROM sample_histories
            WHERE sample_id = :sample_id
            ORDER BY created_at DESC
            """
        ),
        {"sample_id": sample_id},
    )

    return [dict(row._mapping) for row in result]


@router.patch("/{sample_id}")
def update_sample(
    sample_id: str,
    payload: dict,
    db: Session = Depends(get_db),
):
    get_sample_or_404(sample_id, db)

    result = db.execute(
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

    db.commit()

    return dict(result.fetchone()._mapping)


@router.post("/{sample_id}/actions")
def sample_action(
    sample_id: str,
    payload: dict,
    db: Session = Depends(get_db),
):
    sample = get_sample_or_404(sample_id, db)
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

    # TODO(auth):
    # operator_name 目前先由 request body 傳入文字，格式建議為「實驗室／姓名」。
    # 等 /api/me 完成後，改由登入者資訊自動帶入：
    # operator_user_id = current_user.id
    # operator_name = current_user.name
    # operator_lab = current_user.lab_name
    operator_name = payload.get("operator_name")

    if not operator_name:
        raise HTTPException(
            status_code=400,
            detail="operator_name is required",
        )

    if action == "receive":
        result = db.execute(
            text(
                """
                UPDATE samples
                SET
                    status = 'received',
                    current_location = COALESCE(:current_location, '收樣區'),
                    received_at = NOW(),
                    received_by = :operator_name,
                    updated_at = NOW()
                WHERE id = :sample_id
                RETURNING *
                """
            ),
            {
                "sample_id": sample_id,
                "current_location": payload.get("current_location"),
                "operator_name": operator_name,
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
                    operator_name
                )
                VALUES (
                    :sample_id,
                    'receive',
                    :from_status,
                    'received',
                    '確認收樣',
                    :operator_name
                )
                """
            ),
            {
                "sample_id": sample_id,
                "from_status": sample["status"],
                "operator_name": operator_name,
            },
        )

        db.commit()

        return dict(result.fetchone()._mapping)

    if action == "inbound":
        storage_location_id = payload.get("storage_location_id")

        if storage_location_id:
            validate_uuid(storage_location_id, "storage_location_id")

        result = db.execute(
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

        db.execute(
            text(
                """
                INSERT INTO sample_histories (
                    sample_id,
                    action,
                    from_status,
                    to_status,
                    description,
                    operator_name
                )
                VALUES (
                    :sample_id,
                    'inbound',
                    :from_status,
                    'in_storage',
                    '樣品入庫',
                    :operator_name
                )
                """
            ),
            {
                "sample_id": sample_id,
                "from_status": sample["status"],
                "operator_name": operator_name,
            },
        )

        db.commit()

        return dict(result.fetchone()._mapping)

    if action == "outbound":
        result = db.execute(
            text(
                """
                UPDATE samples
                SET
                    status = 'outbound',
                    current_location = COALESCE(:current_location, '待取件區'),
                    updated_at = NOW()
                WHERE id = :sample_id
                RETURNING *
                """
            ),
            {
                "sample_id": sample_id,
                "current_location": payload.get("current_location"),
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
                    operator_name
                )
                VALUES (
                    :sample_id,
                    'outbound',
                    :from_status,
                    'outbound',
                    '樣品出庫',
                    :operator_name
                )
                """
            ),
            {
                "sample_id": sample_id,
                "from_status": sample["status"],
                "operator_name": operator_name,
            },
        )

        db.commit()

        return dict(result.fetchone()._mapping)

    if action == "pickup_confirmed":
        result = db.execute(
            text(
                """
                UPDATE samples
                SET
                    status = 'picked_up',
                    current_location = COALESCE(:current_location, '已取件'),
                    picked_up_at = NOW(),
                    picked_up_by = :operator_name,
                    updated_at = NOW()
                WHERE id = :sample_id
                RETURNING *
                """
            ),
            {
                "sample_id": sample_id,
                "current_location": payload.get("current_location"),
                "operator_name": operator_name,
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
                    operator_name
                )
                VALUES (
                    :sample_id,
                    'pickup_confirmed',
                    :from_status,
                    'picked_up',
                    '廠區確認取件',
                    :operator_name
                )
                """
            ),
            {
                "sample_id": sample_id,
                "from_status": sample["status"],
                "operator_name": operator_name,
            },
        )

        db.commit()

        return dict(result.fetchone()._mapping)

    if action == "split":
        wips = payload.get("wips")

        if not isinstance(wips, list) or len(wips) == 0:
            raise HTTPException(
                status_code=400,
                detail="wips must be a non-empty list when action is split",
            )

        created_wips = []

        db.execute(
            text(
                """
                UPDATE samples
                SET
                    status = 'split',
                    updated_at = NOW()
                WHERE id = :sample_id
                """
            ),
            {"sample_id": sample_id},
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
                    operator_name
                )
                VALUES (
                    :sample_id,
                    'split',
                    :from_status,
                    'split',
                    '樣品分貨並建立 WIP',
                    :operator_name
                )
                """
            ),
            {
                "sample_id": sample_id,
                "from_status": sample["status"],
                "operator_name": operator_name,
            },
        )

        for item in wips:
            result = db.execute(
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
                    "wip_no": item.get("wip_no"),
                    "sample_id": sample_id,
                    "order_no": sample["order_no"],
                    "lab_name": item.get("lab_name"),
                    "experiment_item": item.get("experiment_item"),
                    "priority": item.get("priority", "normal"),
                    "current_location": item.get("current_location", sample["current_location"]),
                    "note": item.get("note"),
                },
            )

            created_wip = dict(result.fetchone()._mapping)
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
                    "description": f"由樣品 {sample['sample_no']} 分貨建立 WIP",
                    "operator_name": operator_name,
                },
            )

        db.commit()

        return {
            "message": "Sample split successfully",
            "sample_id": sample_id,
            "created_wips": created_wips,
        }

    raise HTTPException(status_code=400, detail="Unsupported action")

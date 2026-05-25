from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def row_to_dict(row):
    return dict(row._mapping) if row is not None else None


async def list_transfers(
    db: AsyncSession,
    where_clauses: list[str] | None = None,
    params: dict | None = None,
) -> list[dict]:
    where_clauses = where_clauses or []
    params = params or {}

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

    return [dict(row._mapping) for row in result.fetchall()]


async def count_transfers(db: AsyncSession) -> int:
    result = await db.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM transfers
            """
        )
    )

    row = result.fetchone()
    if row is None:
        raise RuntimeError("Expected row, got None")

    return int(row._mapping["total"])


async def transfer_no_exists(db: AsyncSession, transfer_no: str) -> bool:
    result = await db.execute(
        text(
            """
            SELECT 1
            FROM transfers
            WHERE transfer_no = :transfer_no
            LIMIT 1
            """
        ),
        {"transfer_no": transfer_no},
    )

    return result.fetchone() is not None


async def get_transfer_by_id(db: AsyncSession, transfer_id: str) -> dict | None:
    result = await db.execute(
        text(
            """
            SELECT *
            FROM transfers
            WHERE id = :transfer_id
            """
        ),
        {"transfer_id": transfer_id},
    )

    return row_to_dict(result.fetchone())


async def get_sample_by_id(db: AsyncSession, sample_id: str) -> dict | None:
    result = await db.execute(
        text(
            """
            SELECT *
            FROM samples
            WHERE id = :sample_id
            """
        ),
        {"sample_id": sample_id},
    )

    return row_to_dict(result.fetchone())


async def get_wip_by_id(db: AsyncSession, wip_id: str) -> dict | None:
    result = await db.execute(
        text(
            """
            SELECT *
            FROM wips
            WHERE id = :wip_id
            """
        ),
        {"wip_id": wip_id},
    )

    return row_to_dict(result.fetchone())


async def get_active_transfer_for_target(
    db: AsyncSession,
    target_type: str,
    target_id: str,
) -> dict | None:
    result = await db.execute(
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

    return row_to_dict(result.fetchone())


async def get_pending_sample_transfer(
    db: AsyncSession,
    *,
    sample_id: str,
    from_lab: str,
    to_lab: str,
) -> dict | None:
    result = await db.execute(
        text(
            """
            SELECT *
            FROM transfers
            WHERE target_type = 'sample'
              AND target_id = :sample_id
              AND from_lab = :from_lab
              AND to_lab = :to_lab
              AND status = 'pending'
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {
            "sample_id": sample_id,
            "from_lab": from_lab,
            "to_lab": to_lab,
        },
    )

    return row_to_dict(result.fetchone())


async def create_transfer(
    db: AsyncSession,
    *,
    transfer_no: str,
    target_type: str,
    target_id: str,
    order_no: str | None,
    sample_no: str | None,
    wip_no: str | None,
    from_lab: str,
    to_lab: str,
    handed_by: str,
    note: str | None,
) -> dict:
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
            "transfer_no": transfer_no,
            "target_type": target_type,
            "target_id": target_id,
            "order_no": order_no,
            "sample_no": sample_no,
            "wip_no": wip_no,
            "from_lab": from_lab,
            "to_lab": to_lab,
            "handed_by": handed_by,
            "note": note,
        },
    )

    row = result.fetchone()
    if row is None:
        raise RuntimeError("Expected row, got None")

    return dict(row._mapping)


async def create_pending_sample_transfer(
    db: AsyncSession,
    *,
    transfer_no: str,
    sample_id: str,
    order_no: str | None,
    sample_no: str | None,
    from_lab: str,
    to_lab: str,
    handed_by: str | None,
    note: str | None,
) -> dict:
    result = await db.execute(
        text(
            """
            INSERT INTO transfers (
                transfer_no,
                target_type,
                target_id,
                order_no,
                sample_no,
                from_lab,
                to_lab,
                handed_by,
                status,
                note
            )
            VALUES (
                :transfer_no,
                'sample',
                :sample_id,
                :order_no,
                :sample_no,
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
            "transfer_no": transfer_no,
            "sample_id": sample_id,
            "order_no": order_no,
            "sample_no": sample_no,
            "from_lab": from_lab,
            "to_lab": to_lab,
            "handed_by": handed_by,
            "note": note,
        },
    )

    row = result.fetchone()
    if row is None:
        raise RuntimeError("Expected row, got None")

    return dict(row._mapping)


async def mark_transfer_as_transferring(db: AsyncSession, transfer_id: str) -> None:
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


async def cancel_transfer(db: AsyncSession, transfer_id: str) -> None:
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


async def update_sample_location(
    db: AsyncSession,
    *,
    sample_id: str,
    location: str,
) -> None:
    await db.execute(
        text(
            """
            UPDATE samples
            SET
                current_location = :location,
                updated_at = NOW()
            WHERE id = :sample_id
            """
        ),
        {
            "sample_id": sample_id,
            "location": location,
        },
    )


async def mark_sample_as_pending_receive(
    db: AsyncSession,
    *,
    sample_id: str,
    next_location: str,
) -> None:
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
            "sample_id": sample_id,
            "next_location": next_location,
        },
    )


async def update_wip_location(
    db: AsyncSession,
    *,
    wip_id: str,
    location: str,
) -> None:
    await db.execute(
        text(
            """
            UPDATE wips
            SET
                current_location = :location,
                updated_at = NOW()
            WHERE id = :wip_id
            """
        ),
        {
            "wip_id": wip_id,
            "location": location,
        },
    )


async def update_next_lab_wips_location(
    db: AsyncSession,
    *,
    sample_id: str,
    to_lab: str | None,
    next_location: str,
) -> None:
    if not to_lab:
        return

    await db.execute(
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


async def create_sample_history(
    db: AsyncSession,
    *,
    sample_id: str,
    action: str,
    from_status: str | None,
    to_status: str | None,
    description: str,
    operator_name: str,
    lab_name: str | None,
) -> None:
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
                :action,
                :from_status,
                :to_status,
                :description,
                :operator_name,
                :lab_name
            )
            """
        ),
        {
            "sample_id": sample_id,
            "action": action,
            "from_status": from_status,
            "to_status": to_status,
            "description": description,
            "operator_name": operator_name,
            "lab_name": lab_name,
        },
    )


async def create_wip_history(
    db: AsyncSession,
    *,
    wip_id: str,
    action: str,
    from_status: str | None,
    to_status: str | None,
    description: str,
    operator_name: str,
) -> None:
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
                :action,
                :from_status,
                :to_status,
                :description,
                :operator_name
            )
            """
        ),
        {
            "wip_id": wip_id,
            "action": action,
            "from_status": from_status,
            "to_status": to_status,
            "description": description,
            "operator_name": operator_name,
        },
    )


async def get_transferring_sample_transfer_for_receive(
    db: AsyncSession,
    *,
    sample_id: str,
    current_lab: str | None,
) -> dict | None:
    result = await db.execute(
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

    return row_to_dict(result.fetchone())


async def mark_sample_transfer_as_received(
    db: AsyncSession,
    *,
    sample_id: str,
    current_lab: str | None,
    operator_name: str,
) -> None:
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


async def get_active_sample_transfer_summary(
    db: AsyncSession,
    sample_id: str,
) -> dict | None:
    result = await db.execute(
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

    return row_to_dict(result.fetchone())

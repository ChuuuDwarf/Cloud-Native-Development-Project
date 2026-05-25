from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def row_to_dict(row):
    return dict(row._mapping) if row is not None else None


def rows_to_dicts(rows):
    return [dict(row._mapping) for row in rows]


async def list_samples(
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

    return rows_to_dicts(result.fetchall())


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


async def has_related_lab_sample_access(
    db: AsyncSession,
    *,
    sample_id: str,
    current_lab: str,
) -> bool:
    result = await db.execute(
        text(
            """
            SELECT 1
            WHERE EXISTS (
                SELECT 1
                FROM wips
                WHERE sample_id = :sample_id
                  AND lab_name = :current_lab
            )
            OR EXISTS (
                SELECT 1
                FROM transfers
                WHERE target_type = 'sample'
                  AND target_id = :sample_id
                  AND (
                      from_lab = :current_lab
                      OR to_lab = :current_lab
                  )
            )
            LIMIT 1
            """
        ),
        {
            "sample_id": sample_id,
            "current_lab": current_lab,
        },
    )

    return result.fetchone() is not None


async def list_sample_history(
    db: AsyncSession,
    *,
    where_clauses: list[str],
    params: dict,
) -> list[dict]:
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

    return rows_to_dicts(result.fetchall())


async def update_sample_fields(
    db: AsyncSession,
    *,
    sample_id: str,
    sample_name: str | None,
    experiment_item: str | None,
    current_location: str | None,
    note: str | None,
) -> dict:
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
            "sample_name": sample_name,
            "experiment_item": experiment_item,
            "current_location": current_location,
            "note": note,
        },
    )

    return dict(result.fetchone()._mapping)


async def update_sample_as_received(
    db: AsyncSession,
    *,
    sample_id: str,
    next_location: str,
    operator_name: str,
) -> dict:
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

    return dict(result.fetchone()._mapping)


async def update_sample_as_in_storage(
    db: AsyncSession,
    *,
    sample_id: str,
    current_location: str | None,
    storage_location_id: str | None,
) -> dict:
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
            "current_location": current_location,
            "storage_location_id": storage_location_id,
        },
    )

    return dict(result.fetchone()._mapping)


async def update_sample_as_outbound(
    db: AsyncSession,
    *,
    sample_id: str,
    next_location: str,
    note: str | None,
) -> dict:
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
            "note": note,
        },
    )

    return dict(result.fetchone()._mapping)


async def update_sample_as_picked_up(
    db: AsyncSession,
    *,
    sample_id: str,
    next_location: str,
    operator_name: str,
) -> dict:
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

    return dict(result.fetchone()._mapping)


async def update_sample_as_split(
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


async def update_current_lab_wips_location(
    db: AsyncSession,
    *,
    sample_id: str,
    current_lab: str | None,
    next_location: str,
) -> None:
    if not current_lab:
        return

    await db.execute(
        text(
            """
            UPDATE wips
            SET
                current_location = :next_location,
                updated_at = NOW()
            WHERE sample_id = :sample_id
              AND lab_name = :current_lab
              AND status <> 'completed'
            """
        ),
        {
            "sample_id": sample_id,
            "current_lab": current_lab,
            "next_location": next_location,
        },
    )


async def update_all_wips_location(
    db: AsyncSession,
    *,
    sample_id: str,
    next_location: str,
) -> None:
    await db.execute(
        text(
            """
            UPDATE wips
            SET
                current_location = :next_location,
                updated_at = NOW()
            WHERE sample_id = :sample_id
            """
        ),
        {
            "sample_id": sample_id,
            "next_location": next_location,
        },
    )


async def get_lab_code_by_name_or_code(
    db: AsyncSession,
    *,
    lab_name: str,
) -> str | None:
    result = await db.execute(
        text(
            """
            SELECT code
            FROM labs
            WHERE name = :lab_name
               OR code = :lab_name
            LIMIT 1
            """
        ),
        {"lab_name": lab_name},
    )

    row = result.fetchone()
    return row._mapping["code"] if row is not None else None


async def wip_no_exists(
    db: AsyncSession,
    *,
    wip_no: str,
) -> bool:
    result = await db.execute(
        text(
            """
            SELECT 1
            FROM wips
            WHERE wip_no = :wip_no
            LIMIT 1
            """
        ),
        {"wip_no": wip_no},
    )

    return result.fetchone() is not None


async def list_incomplete_wips_for_sample(
    db: AsyncSession,
    *,
    sample_id: str,
) -> list[dict]:
    result = await db.execute(
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

    return rows_to_dicts(result.fetchall())


async def list_completed_wips_for_sample(
    db: AsyncSession,
    *,
    sample_id: str,
) -> list[dict]:
    result = await db.execute(
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

    return rows_to_dicts(result.fetchall())


async def list_sample_wips_in_flow_order(
    db: AsyncSession,
    *,
    sample_id: str,
) -> list[dict]:
    result = await db.execute(
        text(
            """
            SELECT *
            FROM wips
            WHERE sample_id = :sample_id
            ORDER BY created_at ASC, wip_no ASC, id ASC
            """
        ),
        {"sample_id": sample_id},
    )

    return rows_to_dicts(result.fetchall())


async def get_existing_wip(
    db: AsyncSession,
    *,
    sample_id: str,
    lab_name: str,
    experiment_item: str,
) -> dict | None:
    result = await db.execute(
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

    return row_to_dict(result.fetchone())


async def create_wip_from_split(
    db: AsyncSession,
    *,
    wip_no: str,
    sample_id: str,
    order_no: str | None,
    lab_name: str,
    experiment_item: str,
    priority: str,
    current_location: str,
    note: str | None,
) -> dict:
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
            "order_no": order_no,
            "lab_name": lab_name,
            "experiment_item": experiment_item,
            "priority": priority,
            "current_location": current_location,
            "note": note,
        },
    )

    return dict(result.fetchone()._mapping)


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
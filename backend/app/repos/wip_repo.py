from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession


def row_to_dict(row):
    return dict(row._mapping) if row is not None else None


def rows_to_dicts(rows):
    return [dict(row._mapping) for row in rows]


async def list_dependency_order_items_for_sample(
    db: AsyncSession,
    *,
    sample_no: str,
    order_no: str | None = None,
) -> list[dict]:
    where_order_no = "AND o.order_no = :order_no" if order_no else ""
    params = {"sample_no": sample_no}
    if order_no:
        params["order_no"] = order_no

    result = await db.execute(
        text(
            f"""
            SELECT
                oi.id,
                oi.order_id,
                o.order_no,
                oi.sample_id AS sample_no,
                oi.sample_name,
                oi.lab_id,
                COALESCE(l.name, oi.lab_id) AS lab_name,
                COALESCE(l.code, oi.lab_id) AS lab_code,
                oi.experiment_id,
                COALESCE(lc.experiment_item, oi.experiment_id) AS experiment_name,
                oi.target_group,
                oi.target,
                oi.dependency_check,
                oi.created_at
            FROM order_items oi
            JOIN orders o
                ON o.id = oi.order_id
            LEFT JOIN labs l
                ON CAST(l.id AS TEXT) = oi.lab_id
                OR l.code = oi.lab_id
            LEFT JOIN lab_capabilities lc
                ON CAST(lc.id AS TEXT) = oi.experiment_id
            WHERE oi.sample_id = :sample_no
              {where_order_no}
            ORDER BY o.created_at DESC, oi.target ASC, oi.created_at ASC, oi.id ASC
            """
        ),
        params,
    )

    return rows_to_dicts(result.fetchall())


async def list_machines_for_dependency_candidates(
    db: AsyncSession,
    *,
    lab_names: list[str],
    lab_codes: list[str],
) -> list[dict]:
    if not lab_names and not lab_codes:
        return []

    result = await db.execute(
        text(
            """
            SELECT
                machine_id,
                lab,
                supported_items,
                utilization,
                status
            FROM machines
            WHERE lab IN :lab_values
            """
        ).bindparams(bindparam("lab_values", expanding=True)),
        {"lab_values": (*lab_names, *lab_codes)},
    )

    return rows_to_dicts(result.fetchall())


async def claim_order_item_dependency_check(
    db: AsyncSession,
    *,
    order_item_id: int,
) -> dict | None:
    result = await db.execute(
        text(
            """
            UPDATE order_items
            SET
                dependency_check = true,
                updated_at = NOW()
            WHERE id = :order_item_id
              AND dependency_check = false
            RETURNING
                id,
                order_id,
                sample_id AS sample_no,
                lab_id,
                experiment_id,
                target_group,
                target,
                dependency_check
            """
        ),
        {"order_item_id": order_item_id},
    )

    return row_to_dict(result.fetchone())


async def list_wips(
    db: AsyncSession,
    *,
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
                w.id,
                w.wip_no,
                w.sample_id,
                w.order_no,
                w.lab_name,
                w.experiment_item,
                w.priority,
                w.status,
                w.progress,
                w.current_location,
                w.scheduled_at,
                w.dispatched_at,
                w.started_at,
                w.completed_at,
                w.terminated_at,
                w.note,
                w.created_at,
                w.updated_at
            FROM wips w
            LEFT JOIN samples s
                ON s.id = w.sample_id
            {where_sql}
            ORDER BY w.created_at DESC
            """
        ),
        params,
    )

    return rows_to_dicts(result.fetchall())


async def get_wip_by_id(
    db: AsyncSession,
    *,
    wip_id: str,
) -> dict | None:
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


async def get_sample_by_id(
    db: AsyncSession,
    *,
    sample_id: str,
) -> dict | None:
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

async def get_sample_by_no(
    db: AsyncSession,
    *,
    sample_no: str,
    order_no: str | None = None,
) -> dict | None:
    where_order_no = "AND order_no = :order_no" if order_no else ""
    params = {"sample_no": sample_no}

    if order_no:
        params["order_no"] = order_no

    result = await db.execute(
        text(
            f"""
            SELECT *
            FROM samples
            WHERE sample_no = :sample_no
              {where_order_no}
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        params,
    )

    return row_to_dict(result.fetchone())


async def list_wips_for_sample_no(
    db: AsyncSession,
    *,
    sample_no: str,
    order_no: str | None = None,
) -> list[dict]:
    where_order_no = "AND s.order_no = :order_no" if order_no else ""
    params = {"sample_no": sample_no}

    if order_no:
        params["order_no"] = order_no

    result = await db.execute(
        text(
            f"""
            SELECT
                w.*
            FROM wips w
            JOIN samples s
                ON s.id = w.sample_id
            WHERE s.sample_no = :sample_no
              {where_order_no}
            ORDER BY w.created_at ASC, w.id ASC
            """
        ),
        params,
    )

    return rows_to_dicts(result.fetchall())

async def has_transfer_to_lab_for_sample(
    db: AsyncSession,
    *,
    sample_id: str,
    current_lab: str,
) -> bool:
    result = await db.execute(
        text(
            """
            SELECT 1
            FROM transfers t
            WHERE t.target_type = 'sample'
              AND t.target_id = :sample_id
              AND t.to_lab = :current_lab
            LIMIT 1
            """
        ),
        {
            "sample_id": sample_id,
            "current_lab": current_lab,
        },
    )

    return result.fetchone() is not None


async def list_wip_history(
    db: AsyncSession,
    *,
    wip_id: str,
) -> list[dict]:
    result = await db.execute(
        text(
            """
            SELECT
                id,
                wip_id,
                action,
                from_status,
                to_status,
                description,
                operator_name,
                created_at
            FROM wip_histories
            WHERE wip_id = :wip_id
            ORDER BY created_at DESC
            """
        ),
        {"wip_id": wip_id},
    )

    return rows_to_dicts(result.fetchall())


async def update_wip_fields(
    db: AsyncSession,
    *,
    wip_id: str,
    lab_name: str | None,
    experiment_item: str | None,
    priority: str | None,
    current_location: str | None,
    note: str | None,
) -> dict:
    result = await db.execute(
        text(
            """
            UPDATE wips
            SET
                lab_name = COALESCE(:lab_name, lab_name),
                experiment_item = COALESCE(:experiment_item, experiment_item),
                priority = COALESCE(:priority, priority),
                current_location = COALESCE(:current_location, current_location),
                note = COALESCE(:note, note),
                updated_at = NOW()
            WHERE id = :wip_id
            RETURNING *
            """
        ),
        {
            "wip_id": wip_id,
            "lab_name": lab_name,
            "experiment_item": experiment_item,
            "priority": priority,
            "current_location": current_location,
            "note": note,
        },
    )

    row = result.fetchone()
    if row is None:
        raise RuntimeError(f"WIP not found: {wip_id}")

    return dict(row._mapping)


async def update_wip_status(
    db: AsyncSession,
    *,
    wip_id: str,
    new_status: str,
    scheduled_at: bool = False,
    dispatched_at: bool = False,
    started_at: bool = False,
    completed_at: bool = False,
    terminated_at: bool = False,
    progress: int | None = None,
    next_location: str | None = None,
) -> dict:
    extra_sql = ""
    params: dict[str, object] = {
        "wip_id": wip_id,
        "new_status": new_status,
    }

    if scheduled_at:
        extra_sql += ", scheduled_at = NOW()"

    if dispatched_at:
        extra_sql += ", dispatched_at = NOW()"

    if started_at:
        extra_sql += ", started_at = NOW()"

    if completed_at:
        extra_sql += ", completed_at = NOW()"

    if terminated_at:
        extra_sql += ", terminated_at = NOW()"

    if progress is not None:
        extra_sql += ", progress = :progress"
        params["progress"] = progress

    if next_location:
        extra_sql += ", current_location = :next_location"
        params["next_location"] = next_location

    result = await db.execute(
        text(
            f"""
            UPDATE wips
            SET
                status = :new_status,
                updated_at = NOW()
                {extra_sql}
            WHERE id = :wip_id
            RETURNING *
            """
        ),
        params,
    )

    row = result.fetchone()
    if row is None:
        raise RuntimeError(f"WIP not found: {wip_id}")

    return dict(row._mapping)


async def update_sample_location(
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


async def update_sample_status_and_location(
    db: AsyncSession,
    *,
    sample_id: str,
    status: str,
    current_location: str,
) -> None:
    await db.execute(
        text(
            """
            UPDATE samples
            SET
                status = :status,
                current_location = :current_location,
                updated_at = NOW()
            WHERE id = :sample_id
            """
        ),
        {
            "sample_id": sample_id,
            "status": status,
            "current_location": current_location,
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


async def get_latest_completed_wip_for_lab(
    db: AsyncSession,
    *,
    sample_id: str,
    current_lab: str | None,
) -> dict | None:
    result = await db.execute(
        text(
            """
            SELECT *
            FROM wips
            WHERE sample_id = :sample_id
              AND lab_name = :current_lab
              AND status = 'completed'
            ORDER BY completed_at IS NULL ASC, completed_at DESC, updated_at DESC
            LIMIT 1
            """
        ),
        {
            "sample_id": sample_id,
            "current_lab": current_lab,
        },
    )

    return row_to_dict(result.fetchone())


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

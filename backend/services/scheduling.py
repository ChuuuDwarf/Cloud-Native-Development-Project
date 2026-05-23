from datetime import datetime, timedelta
from typing import Any

from dependencies import lab_filter_sql
from schemas import ScheduleStrategy, User


REPLAN_STRATEGIES: dict[str, ScheduleStrategy] = {
    "機台故障重排": "Least Setup Change",
    "特急單插單重排": "Priority First",
    "前站延誤重排": "Earliest Due Date",
    "人員不足重排": "Hybrid",
}


def priority_rank(priority: str) -> int:
    return {"特急": 0, "高": 1, "一般": 2}.get(priority, 3)


def sorted_dispatches(
    dispatch_rows: list[dict[str, Any]], strategy: ScheduleStrategy
) -> list[dict[str, Any]]:
    if strategy == "Priority First":
        return sorted(
            dispatch_rows,
            key=lambda row: (priority_rank(str(row["priority"])), str(row["due_at"])),
        )
    if strategy == "Earliest Due Date":
        return sorted(
            dispatch_rows,
            key=lambda row: (str(row["due_at"]), priority_rank(str(row["priority"]))),
        )
    if strategy == "Least Setup Change":
        return sorted(
            dispatch_rows,
            key=lambda row: (str(row["experiment_item"]), str(row["dispatch_id"])),
        )
    if strategy == "Hybrid":
        return sorted(
            dispatch_rows,
            key=lambda row: (
                priority_rank(str(row["priority"])),
                str(row["due_at"]),
                str(row["experiment_item"]),
            ),
        )
    return sorted(dispatch_rows, key=lambda row: str(row["dispatch_id"]))


def apply_schedule_suggestion(
    conn: Any,
    strategy: ScheduleStrategy,
    user: User,
    replan_reason: str | None = None,
) -> list[dict[str, Any]]:
    dispatch_filter, dispatch_params = lab_filter_sql(user)
    dispatch_rows = conn.execute(
        f"""
        SELECT *
        FROM dispatches
        {dispatch_filter if dispatch_filter else "WHERE TRUE"}
          AND status IN ('待派工', '排程中')
        ORDER BY dispatch_id
        """,
        dispatch_params,
    ).fetchall()
    dispatch_rows = sorted_dispatches(dispatch_rows, strategy)
    machine_filter, machine_params = lab_filter_sql(user)
    machine_rows = conn.execute(
        f"""
        SELECT *
        FROM machines
        {machine_filter if machine_filter else "WHERE TRUE"}
          AND status NOT IN ('故障中', '保養中', '停用')
        ORDER BY utilization ASC, machine_id ASC
        """,
        machine_params,
    ).fetchall()

    shift_start = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    for index, dispatch in enumerate(dispatch_rows):
        matched_machine = next(
            (
                machine
                for machine in machine_rows
                if dispatch["experiment_item"] in machine["supported_items"]
                and dispatch["lab"] == machine["lab"]
            ),
            None,
        )
        if matched_machine is not None:
            scheduled_start = shift_start + timedelta(hours=index * 2)
            scheduled_end = scheduled_start + timedelta(hours=2)
            conn.execute(
                """
                UPDATE dispatches
                SET status = '排程中',
                    suggested_machine_id = %s,
                    scheduled_start = %s,
                    scheduled_end = %s,
                    strategy = %s,
                    replan_reason = %s
                WHERE dispatch_id = %s
                """,
                (
                    matched_machine["machine_id"],
                    scheduled_start.strftime("%Y-%m-%d %H:%M"),
                    scheduled_end.strftime("%Y-%m-%d %H:%M"),
                    strategy,
                    replan_reason,
                    dispatch["dispatch_id"],
                ),
            )

    return conn.execute(
        f"""
        SELECT *
        FROM dispatches
        {dispatch_filter}
        ORDER BY
            CASE WHEN scheduled_start IS NULL THEN 1 ELSE 0 END,
            scheduled_start ASC,
            dispatch_id ASC
        """,
        dispatch_params,
    ).fetchall()

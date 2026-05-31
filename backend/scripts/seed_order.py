from __future__ import annotations

import os
import random
import string
from datetime import datetime, timezone

import psycopg


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:123@localhost:5432/lims_db",
)

DEBUG_ORDERS = [
    {
        "sample_id": "DEBUG-DEP-001",
        "sample_name": "DEBUG dependency 001",
        "items": "G2#1|電性測試實驗室:Probe、G1#1|材料分析實驗室:EDX、G1#2|材料分析實驗室:SEM、G1#3|電性測試實驗室:IV",
    },
    {
        "sample_id": "DEBUG-DEP-002",
        "sample_name": "DEBUG dependency 002",
        "items": "G3#1|材料分析實驗室:EDX、G1#1|材料分析實驗室:FIB、G2#1|電性測試實驗室:CV",
    },
]


def now():
    return datetime.now(timezone.utc)


def random_suffix(length: int = 4) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


def parse_items(text: str) -> list[dict]:
    result = []

    for raw_part in text.split("、"):
        part = raw_part.strip()
        if not part:
            continue

        prefix, body = part.split("|", 1)
        target_group, target_text = prefix.split("#", 1)
        lab_name, experiment_name = body.split(":", 1)

        result.append(
            {
                "target_group": target_group.strip(),
                "target": int(target_text.strip()),
                "lab_name": lab_name.strip(),
                "experiment_name": experiment_name.strip(),
            }
        )

    return result


def fetch_one_value(conn, sql: str, params: tuple = ()):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return row[0] if row else None


def get_applicant_id(conn) -> str:
    applicant_id = fetch_one_value(
        conn,
        """
        SELECT u.id::text
        FROM users u
        JOIN user_roles ur ON ur.user_id = u.id
        JOIN roles r ON r.id = ur.role_id
        WHERE r.name = 'plant_user'
          AND u.is_active = TRUE
        ORDER BY u.created_at ASC
        LIMIT 1
        """,
    )

    if not applicant_id:
        raise RuntimeError("找不到 plant_user，請先確認 users / roles / user_roles seed data")

    return applicant_id


def get_department_id(conn) -> str:
    department_id = fetch_one_value(
        conn,
        """
        SELECT id::text
        FROM departments
        WHERE is_active = TRUE
        ORDER BY created_at ASC
        LIMIT 1
        """,
    )

    if not department_id:
        raise RuntimeError("找不到 departments，請先建立至少一個啟用中的部門")

    return department_id


def get_lab_id(conn, lab_name: str) -> str:
    lab_id = fetch_one_value(
        conn,
        """
        SELECT id::text
        FROM labs
        WHERE name = %s
          AND is_active = TRUE
        LIMIT 1
        """,
        (lab_name,),
    )

    if not lab_id:
        raise RuntimeError(f"找不到實驗室：{lab_name}")

    return lab_id


def get_experiment_id(conn, lab_id: str, experiment_name: str) -> str:
    experiment_id = fetch_one_value(
        conn,
        """
        SELECT id::text
        FROM lab_capabilities
        WHERE lab_id = %s::uuid
          AND experiment_item = %s
        LIMIT 1
        """,
        (lab_id, experiment_name),
    )

    if not experiment_id:
        raise RuntimeError(f"找不到實驗項目：lab_id={lab_id}, experiment={experiment_name}")

    return experiment_id


def get_lab_supervisor_id(conn, lab_id: str) -> str | None:
    return fetch_one_value(
        conn,
        """
        SELECT u.id::text
        FROM users u
        JOIN user_roles ur ON ur.user_id = u.id
        JOIN roles r ON r.id = ur.role_id
        WHERE r.name = 'lab_supervisor'
          AND u.lab_id = %s::uuid
          AND u.is_active = TRUE
        ORDER BY u.created_at ASC
        LIMIT 1
        """,
        (lab_id,),
    )


def delete_old_debug_orders(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM orders
            WHERE order_no LIKE 'DBG-DEP-%'
               OR order_no LIKE 'ORD-DEBUG-DEP-%'
               OR id IN (
                    SELECT DISTINCT order_id
                    FROM order_items
                    WHERE sample_id IN ('DEBUG-DEP-001', 'DEBUG-DEP-002')
               )
            """
        )


def insert_order(conn, *, applicant_id: str, department_id: str, debug_order: dict) -> dict:
    apply_time = now()

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO orders (
                order_no,
                applicant_id,
                department_id,
                apply_date,
                status,
                priority,
                total_items,
                last_reason,
                is_deleted,
                created_at,
                updated_at
            )
            VALUES (
                %s,
                %s,
                %s,
                %s,
                'approved',
                'normal',
                0,
                NULL,
                FALSE,
                %s,
                %s
            )
            RETURNING id
            """,
            (
                f"DBG-DEP-PENDING-{random_suffix()}",
                applicant_id,
                department_id,
                apply_time,
                apply_time,
                apply_time,
            ),
        )

        order_id = cur.fetchone()[0]
        order_no = f"DBG-DEP-{order_id:03d}-{random_suffix()}"

        cur.execute(
            """
            UPDATE orders
            SET order_no = %s
            WHERE id = %s
            """,
            (order_no, order_id),
        )

        parsed_items = parse_items(debug_order["items"])

        for item in parsed_items:
            lab_id = get_lab_id(conn, item["lab_name"])
            experiment_id = get_experiment_id(conn, lab_id, item["experiment_name"])
            supervisor_id = get_lab_supervisor_id(conn, lab_id)

            cur.execute(
                """
                INSERT INTO order_items (
                    order_id,
                    sample_id,
                    sample_name,
                    lab_id,
                    experiment_id,
                    target_group,
                    target,
                    dependency_check,
                    status,
                    approved_by,
                    approved_at,
                    return_reason,
                    reject_reason,
                    quota_exceeded,
                    quota_override,
                    quota_override_reason,
                    quota_approved_by,
                    quota_approved_at,
                    created_at,
                    updated_at
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    FALSE,
                    'approved',
                    %s,
                    %s,
                    NULL,
                    NULL,
                    FALSE,
                    FALSE,
                    NULL,
                    NULL,
                    NULL,
                    %s,
                    %s
                )
                """,
                (
                    order_id,
                    debug_order["sample_id"],
                    debug_order["sample_name"],
                    lab_id,
                    experiment_id,
                    item["target_group"],
                    item["target"],
                    supervisor_id,
                    apply_time,
                    apply_time,
                    apply_time,
                ),
            )

        cur.execute(
            """
            UPDATE orders
            SET total_items = %s,
                updated_at = %s
            WHERE id = %s
            """,
            (len(parsed_items), apply_time, order_id),
        )

        cur.execute(
            """
            INSERT INTO order_histories (
                order_id,
                actor_id,
                action,
                from_status,
                to_status,
                reason,
                quota_override,
                action_time
            )
            VALUES
                (%s, %s, 'create', NULL, 'draft', 'debug seed', FALSE, %s),
                (%s, %s, 'submit', 'draft', 'pending_approval', 'debug seed', FALSE, %s),
                (%s, %s, 'approve', 'pending_approval', 'approved', 'debug seed approved', FALSE, %s)
            """,
            (
                order_id,
                applicant_id,
                apply_time,
                order_id,
                applicant_id,
                apply_time,
                order_id,
                applicant_id,
                apply_time,
            ),
        )

    return {
        "order_id": order_id,
        "order_no": order_no,
        "sample_id": debug_order["sample_id"],
        "status": "approved",
        "items": debug_order["items"],
    }


def main():
    with psycopg.connect(DATABASE_URL) as conn:
        applicant_id = get_applicant_id(conn)
        department_id = get_department_id(conn)

        delete_old_debug_orders(conn)

        created = []
        for debug_order in DEBUG_ORDERS:
            created.append(
                insert_order(
                    conn,
                    applicant_id=applicant_id,
                    department_id=department_id,
                    debug_order=debug_order,
                )
            )

        conn.commit()

    print("已新增 debug 委託單，狀態都是 approved / 待確認送樣：")
    for item in created:
        print(f"- {item['order_no']} / {item['sample_id']} / {item['status']}")


if __name__ == "__main__":
    main()
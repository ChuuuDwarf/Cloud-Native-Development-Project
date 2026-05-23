from schemas import User
from services.scheduling import (
    REPLAN_STRATEGIES,
    apply_schedule_suggestion,
    priority_rank,
    sorted_dispatches,
)


def dispatch(
    dispatch_id,
    priority="一般",
    due_at="2026-05-24 12:00",
    item="材料成份分析",
    lab="LAB A",
):
    return {
        "dispatch_id": dispatch_id,
        "priority": priority,
        "due_at": due_at,
        "experiment_item": item,
        "lab": lab,
    }


def user(role="實驗室人員", lab="LAB A"):
    return User(
        userId="u-lab-a",
        name="林育誠",
        role=role,
        department="實驗室",
        lab=lab,
    )


def test_priority_rank_orders_known_priorities_before_unknown():
    assert priority_rank("特急") < priority_rank("高") < priority_rank("一般")
    assert priority_rank("未知") == 3


def test_sorted_dispatches_fifo_uses_dispatch_id():
    rows = [dispatch("DSP-002"), dispatch("DSP-001")]

    assert [row["dispatch_id"] for row in sorted_dispatches(rows, "FIFO")] == [
        "DSP-001",
        "DSP-002",
    ]


def test_sorted_dispatches_priority_first_uses_priority_then_due_date():
    rows = [
        dispatch("DSP-001", priority="一般", due_at="2026-05-22 12:00"),
        dispatch("DSP-002", priority="特急", due_at="2026-05-23 12:00"),
        dispatch("DSP-003", priority="特急", due_at="2026-05-21 12:00"),
    ]

    assert [
        row["dispatch_id"] for row in sorted_dispatches(rows, "Priority First")
    ] == [
        "DSP-003",
        "DSP-002",
        "DSP-001",
    ]


def test_sorted_dispatches_earliest_due_date_uses_due_date_then_priority():
    rows = [
        dispatch("DSP-001", priority="特急", due_at="2026-05-24 12:00"),
        dispatch("DSP-002", priority="一般", due_at="2026-05-23 12:00"),
        dispatch("DSP-003", priority="高", due_at="2026-05-23 12:00"),
    ]

    assert [
        row["dispatch_id"] for row in sorted_dispatches(rows, "Earliest Due Date")
    ] == [
        "DSP-003",
        "DSP-002",
        "DSP-001",
    ]


def test_sorted_dispatches_least_setup_change_groups_experiment_items():
    rows = [
        dispatch("DSP-002", item="薄膜應力分析"),
        dispatch("DSP-001", item="材料成份分析"),
        dispatch("DSP-003", item="材料成份分析"),
    ]

    assert [
        row["dispatch_id"] for row in sorted_dispatches(rows, "Least Setup Change")
    ] == [
        "DSP-001",
        "DSP-003",
        "DSP-002",
    ]


def test_replan_strategies_match_business_reasons():
    assert REPLAN_STRATEGIES["機台故障重排"] == "Least Setup Change"
    assert REPLAN_STRATEGIES["特急單插單重排"] == "Priority First"
    assert REPLAN_STRATEGIES["前站延誤重排"] == "Earliest Due Date"
    assert REPLAN_STRATEGIES["人員不足重排"] == "Hybrid"


class _Result:
    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows


class _Conn:
    def __init__(self):
        self.dispatches = [
            {
                **dispatch(
                    "DSP-002", priority="一般", item="薄膜應力分析", lab="LAB B"
                ),
                "status": "待派工",
            },
            {
                **dispatch(
                    "DSP-001", priority="特急", item="材料成份分析", lab="LAB A"
                ),
                "status": "待派工",
            },
        ]
        self.machines = [
            {
                "machine_id": "TEM-001",
                "lab": "LAB A",
                "status": "閒置",
                "supported_items": ["材料成份分析"],
                "utilization": 10,
            },
            {
                "machine_id": "XRD-002",
                "lab": "LAB B",
                "status": "閒置",
                "supported_items": ["薄膜應力分析"],
                "utilization": 5,
            },
        ]
        self.updates = []

    def execute(self, query, params=()):
        if "UPDATE dispatches" in query:
            self.updates.append(params)
            return _Result([])
        if "FROM machines" in query:
            return _Result([row for row in self.machines if row["lab"] == params[0]])
        if "status IN" in query:
            return _Result([row for row in self.dispatches if row["lab"] == params[0]])
        return _Result([row for row in self.dispatches if row["lab"] == params[0]])


def test_apply_schedule_suggestion_updates_only_user_lab_dispatches():
    conn = _Conn()

    rows = apply_schedule_suggestion(conn, "Priority First", user(lab="LAB A"), "插單")

    assert len(conn.updates) == 1
    assert conn.updates[0][0] == "TEM-001"
    assert conn.updates[0][3] == "Priority First"
    assert conn.updates[0][4] == "插單"
    assert conn.updates[0][5] == "DSP-001"
    assert [row["dispatch_id"] for row in rows] == ["DSP-001"]

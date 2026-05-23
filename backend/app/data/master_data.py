from __future__ import annotations

from typing import Any

from app.core.order_errors import bad_request

DEPARTMENTS: list[dict[str, str]] = [
    {"id": "D001", "name": "製造一部"},
    {"id": "D002", "name": "品保部"},
    {"id": "D003", "name": "研發部"},
]

LABS: list[dict[str, str]] = [
    {"id": "LAB001", "name": "可靠度實驗室"},
    {"id": "LAB002", "name": "材料分析實驗室"},
    {"id": "LAB003", "name": "顯微分析實驗室"},
]

EXPERIMENTS: list[dict[str, str]] = [
    {"id": "EXP001", "name": "溫濕度測試", "labId": "LAB001"},
    {"id": "EXP002", "name": "壽命測試", "labId": "LAB001"},
    {"id": "EXP003", "name": "成分分析", "labId": "LAB002"},
    {"id": "EXP004", "name": "SEM 分析", "labId": "LAB003"},
]

SAMPLES = [
    {
        "id": "S001",
        "sampleNo": "S001",
        "name": "樣品 A",
        "status": "available",
        "description": "委託單測試用樣品",
    },
    {
        "id": "S002",
        "sampleNo": "S002",
        "name": "樣品 B",
        "status": "available",
        "description": "委託單測試用樣品",
    },
    {
        "id": "S003",
        "sampleNo": "S003",
        "name": "樣品 C",
        "status": "reserved",
        "description": "委託單測試用樣品",
    },
]

DEPARTMENT_IDS = {item["id"] for item in DEPARTMENTS}
LAB_IDS = {item["id"] for item in LABS}
EXPERIMENT_BY_ID = {item["id"]: item for item in EXPERIMENTS}


def validate_order_master_data(department_id: str, items: list[Any]) -> None:
    if department_id not in DEPARTMENT_IDS:
        raise bad_request(f"Unknown department: {department_id}")

    for index, item in enumerate(items, start=1):
        if item.lab_id not in LAB_IDS:
            raise bad_request(f"Unknown lab in item {index}: {item.lab_id}")

        experiment = EXPERIMENT_BY_ID.get(item.experiment_id)
        if experiment is None:
            raise bad_request(f"Unknown experiment in item {index}: {item.experiment_id}")

        if experiment["labId"] != item.lab_id:
            raise bad_request(
                f"Experiment {item.experiment_id} does not belong to lab {item.lab_id}"
            )

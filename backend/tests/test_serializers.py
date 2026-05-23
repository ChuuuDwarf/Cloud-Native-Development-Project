from datetime import datetime, timezone

from serializers import (
    dispatch_from_row,
    list_response,
    machine_from_row,
    recipe_from_row,
    response,
    user_from_row,
)


def test_response_wraps_data_with_message():
    assert response({"id": 1}, "created") == {"data": {"id": 1}, "message": "created"}


def test_list_response_includes_total():
    assert list_response([1, 2, 3]) == {
        "data": [1, 2, 3],
        "total": 3,
        "message": "success",
    }


def test_machine_from_row_maps_database_names_to_api_names():
    machine = machine_from_row(
        {
            "machine_id": "TEM-001",
            "name": "穿透式電子顯微鏡",
            "lab": "LAB A",
            "status": "閒置",
            "supported_items": ("材料成份分析", "晶格缺陷觀察"),
            "utilization": "48",
            "owner": "林育誠",
            "last_maintenance": "2026-05-10",
        }
    )

    assert machine.machineId == "TEM-001"
    assert machine.supportedItems == ["材料成份分析", "晶格缺陷觀察"]
    assert machine.utilization == 48


def test_user_from_row_preserves_optional_lab():
    user = user_from_row(
        {
            "user_id": "u-admin",
            "name": "張志明",
            "role": "系統管理者",
            "department": "資訊部",
            "lab": None,
        }
    )

    assert user.userId == "u-admin"
    assert user.lab is None


def test_recipe_from_row_formats_updated_at():
    recipe = recipe_from_row(
        {
            "recipe_id": "RCP-001",
            "name": "標準流程",
            "version": "v1.0",
            "experiment_item": "材料成份分析",
            "machine_ids": ["TEM-001"],
            "method": "EDS mapping",
            "parameters": {"voltage": "200kV"},
            "updated_by": "林育誠",
            "updated_at": datetime(2026, 5, 23, 9, 30, tzinfo=timezone.utc),
        }
    )

    assert recipe.recipeId == "RCP-001"
    assert recipe.updatedAt == "2026-05-23 09:30"
    assert recipe.parameters == {"voltage": "200kV"}


def test_dispatch_from_row_maps_nullable_assignment_fields():
    dispatch = dispatch_from_row(
        {
            "dispatch_id": "DSP-001",
            "wip_id": "WIP-001",
            "order_id": "WO-001",
            "experiment_item": "材料成份分析",
            "priority": "特急",
            "lab": "LAB A",
            "due_at": "2026-05-24 12:00",
            "status": "待派工",
            "suggested_machine_id": None,
            "assigned_machine_id": None,
            "assigned_recipe_id": None,
            "scheduled_start": None,
            "scheduled_end": None,
            "created_by": "王建國",
            "assigned_by": None,
            "strategy": None,
            "replan_reason": None,
        }
    )

    assert dispatch.dispatchId == "DSP-001"
    assert dispatch.suggestedMachineId is None
    assert dispatch.createdBy == "王建國"

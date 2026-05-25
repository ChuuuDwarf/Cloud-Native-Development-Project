import pytest
from fastapi import HTTPException

from app.services.wip_service import (
    build_ordered_wip_slots,
    build_wip_visibility_filter,
    can_manage_wip,
    can_view_wip,
    experiment_temp_location,
    find_first_incomplete_wip_slot,
    find_wip_experiment_index_from_slots,
    lab_location,
    machine_location,
    parse_requested_experiments,
    validate_wip_create_items_in_order,
    validate_uuid,
)


def test_wip_location_helpers_match_workflow_locations():
    assert lab_location("Lab A", "實驗暫存區") == "Lab A 實驗暫存區"
    assert machine_location("Lab B") == "Lab B 機台區"
    assert experiment_temp_location("Lab C") == "Lab C 實驗暫存區"


def test_wip_visibility_filter_uses_wip_owner_lab_not_current_location():
    lab_user = {"role": "lab_engineer", "lab_name": "Lab A", "department": "Lab A"}
    clauses, params = build_wip_visibility_filter(lab_user)

    assert clauses == ["w.lab_name = :current_lab"]
    assert params == {"current_lab": "Lab A"}


def test_wip_visibility_filter_for_factory_and_admin():
    factory = {"role": "plant_user", "name": "王小明"}
    clauses, params = build_wip_visibility_filter(factory)
    assert clauses == ["s.applicant_name = :applicant_name"]
    assert params == {"applicant_name": "王小明"}

    assert build_wip_visibility_filter({"role": "system_admin"}) == ([], {})


def test_lab_user_can_manage_own_lab_wip_even_after_location_changes():
    wip = {"lab_name": "Lab A", "current_location": "已由使用者取回"}
    lab_a = {"role": "lab_engineer", "lab_name": "Lab A", "department": "Lab A"}
    lab_b = {"role": "lab_engineer", "lab_name": "Lab B", "department": "Lab B"}

    assert can_view_wip(lab_a, wip) is True
    assert can_manage_wip(lab_a, wip) is True
    assert can_view_wip(lab_b, wip) is False
    assert can_manage_wip(lab_b, wip) is False


def test_plant_user_can_only_view_own_sample_wips():
    wip = {"lab_name": "Lab A"}
    factory = {"role": "plant_user", "name": "王小明"}

    assert can_view_wip(factory, wip, {"applicant_name": "王小明"}) is True
    assert can_view_wip(factory, wip, {"applicant_name": "陳大華"}) is False
    assert can_manage_wip(factory, wip) is False


def test_validate_uuid_rejects_invalid_wip_id():
    validate_uuid("11111111-1111-1111-1111-111111111111", "wip_id")

    with pytest.raises(HTTPException) as exc:
        validate_uuid("bad", "wip_id")

    assert exc.value.status_code == 400
    assert exc.value.detail == "wip_id must be a valid UUID"


def test_wip_order_slots_prevent_skipping_later_same_lab_in_aba_flow():
    experiments = parse_requested_experiments("Lab A:SEM、Lab B:CV、Lab A:EDX")
    wips = [
        {"id": "a-1", "lab_name": "Lab A", "experiment_item": "SEM", "status": "created"},
        {"id": "b-1", "lab_name": "Lab B", "experiment_item": "CV", "status": "created"},
        {"id": "a-2", "lab_name": "Lab A", "experiment_item": "EDX", "status": "created"},
    ]

    slots = build_ordered_wip_slots(experiments, wips)
    first_incomplete = find_first_incomplete_wip_slot(slots)

    assert first_incomplete is not None
    assert first_incomplete["wip"]["id"] == "a-1"
    assert find_wip_experiment_index_from_slots(slots, "a-2") == 2


def test_wip_order_slots_allow_second_same_lab_after_first_completed_in_aab_flow():
    experiments = parse_requested_experiments("Lab A:SEM、Lab A:EDX、Lab B:CV")
    wips = [
        {"id": "a-1", "lab_name": "Lab A", "experiment_item": "SEM", "status": "completed"},
        {"id": "a-2", "lab_name": "Lab A", "experiment_item": "EDX", "status": "created"},
        {"id": "b-1", "lab_name": "Lab B", "experiment_item": "CV", "status": "created"},
    ]

    slots = build_ordered_wip_slots(experiments, wips)
    first_incomplete = find_first_incomplete_wip_slot(slots)

    assert first_incomplete is not None
    assert first_incomplete["wip"]["id"] == "a-2"
    assert find_wip_experiment_index_from_slots(slots, "a-2") == 1


def test_wip_create_order_guard_allows_contiguous_same_lab_wips():
    sample = {"experiment_item": "Lab A:SEM、Lab A:EDX、Lab B:CV"}

    validate_wip_create_items_in_order(
        sample=sample,
        existing_wips=[],
        requested_items=[
            {"lab_name": "Lab A", "experiment_item": "SEM"},
            {"lab_name": "Lab A", "experiment_item": "EDX"},
        ],
    )


def test_wip_create_order_guard_blocks_same_lab_after_intermediate_lab():
    sample = {"experiment_item": "Lab A:SEM、Lab B:CV、Lab A:EDX"}

    with pytest.raises(HTTPException) as exc:
        validate_wip_create_items_in_order(
            sample=sample,
            existing_wips=[],
            requested_items=[
                {"lab_name": "Lab A", "experiment_item": "SEM"},
                {"lab_name": "Lab A", "experiment_item": "EDX"},
            ],
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "目前尚未輪到此 WIP，請先完成前一站實驗或交接流程"


def test_wip_create_order_guard_blocks_skipping_first_contiguous_wip():
    sample = {"experiment_item": "Lab A:SEM、Lab A:EDX、Lab B:CV"}

    with pytest.raises(HTTPException) as exc:
        validate_wip_create_items_in_order(
            sample=sample,
            existing_wips=[],
            requested_items=[
                {"lab_name": "Lab A", "experiment_item": "EDX"},
            ],
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "目前尚未輪到此 WIP，請先完成前一站實驗或交接流程"

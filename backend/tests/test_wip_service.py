import pytest
from fastapi import HTTPException

from app.services.wip_service import (
    build_ordered_wip_slots,
    build_wip_owner_lab_visibility_filter,
    build_wip_visibility_filter,
    can_manage_wip,
    can_view_wip,
    experiment_temp_location,
    find_first_incomplete_wip_slot,
    find_wip_experiment_index_from_slots,
    get_completable_wip_slots_for_current_segment,
    lab_location,
    machine_location,
    machine_utilization_score,
    parse_requested_experiments,
    select_dependency_candidate,
    select_next_dependency_candidates,
    validate_uuid,
    validate_wip_create_items_in_order,
)


def test_wip_location_helpers_match_workflow_locations():
    assert lab_location("Lab A", "實驗暫存區") == "Lab A 實驗暫存區"
    assert machine_location("Lab B") == "Lab B 機台區"
    assert experiment_temp_location("Lab C") == "Lab C 實驗暫存區"


def test_wip_visibility_filter_uses_wip_owner_lab_not_current_location():
    lab_user = {"role": "lab_engineer", "lab_name": "Lab A", "department": "Lab A"}
    clauses, params = build_wip_visibility_filter(lab_user)

    joined = " ".join(clauses)
    assert "w.lab_name = :current_lab" in joined
    assert "FROM transfers t" in joined
    assert "t.to_lab = :current_lab" in joined
    assert params == {"current_lab": "Lab A"}


def test_wip_visibility_filter_for_factory_and_admin():
    factory = {"role": "plant_user", "name": "王小明"}
    clauses, params = build_wip_visibility_filter(factory)
    assert clauses == ["s.applicant_name = :applicant_name"]
    assert params == {"applicant_name": "王小明"}

    assert build_wip_visibility_filter({"role": "system_admin"}) == ([], {})


@pytest.mark.asyncio
async def test_lab_user_can_manage_own_lab_wip_even_after_location_changes():
    wip = {"lab_name": "Lab A", "current_location": "已由使用者取回"}
    lab_a = {"role": "lab_engineer", "lab_name": "Lab A", "department": "Lab A"}
    lab_b = {"role": "lab_engineer", "lab_name": "Lab B", "department": "Lab B"}

    assert await can_view_wip(lab_a, wip) is True
    assert can_manage_wip(lab_a, wip) is True
    assert await can_view_wip(lab_b, wip) is False
    assert can_manage_wip(lab_b, wip) is False


@pytest.mark.asyncio
async def test_plant_user_can_only_view_own_sample_wips():
    wip = {"lab_name": "Lab A"}
    factory = {"role": "plant_user", "name": "王小明"}

    assert await can_view_wip(factory, wip, {"applicant_name": "王小明"}) is True
    assert await can_view_wip(factory, wip, {"applicant_name": "陳大華"}) is False
    assert can_manage_wip(factory, wip) is False


def test_validate_uuid_rejects_invalid_wip_id():
    validate_uuid("11111111-1111-1111-1111-111111111111", "wip_id")

    with pytest.raises(HTTPException) as exc:
        validate_uuid("bad", "wip_id")

    assert exc.value.status_code == 400
    assert exc.value.detail == "wip_id must be a valid UUID"


def test_dependency_candidates_pick_smallest_incomplete_target_per_group():
    items = [
        {"id": 1, "target_group": "G1", "target": 1, "dependency_check": True},
        {"id": 2, "target_group": "G1", "target": 2, "dependency_check": False},
        {"id": 3, "target_group": "G1", "target": 3, "dependency_check": False},
        {"id": 4, "target_group": "G2", "target": 1, "dependency_check": False},
    ]

    candidates = select_next_dependency_candidates(items, [])

    assert [candidate["id"] for candidate in candidates] == [1, 4]


def test_dependency_candidates_skip_completed_wip_and_pick_next_target():
    items = [
        {
            "id": 1,
            "lab_name": "Lab A",
            "experiment_name": "SEM",
            "target_group": "G1",
            "target": 1,
            "dependency_check": True,
        },
        {
            "id": 2,
            "lab_name": "Lab A",
            "experiment_name": "EDX",
            "target_group": "G1",
            "target": 2,
            "dependency_check": False,
        },
        {
            "id": 3,
            "lab_name": "Lab B",
            "experiment_name": "CV",
            "target_group": "G2",
            "target": 1,
            "dependency_check": False,
        },
    ]

    sample_wips = [
        {
            "lab_name": "Lab A",
            "experiment_item": "SEM",
            "status": "completed",
        }
    ]

    candidates = select_next_dependency_candidates(items, sample_wips)

    assert [candidate["id"] for candidate in candidates] == [2, 3]


def test_dependency_tie_break_uses_lowest_machine_utilization():
    candidates = [
        {
            "id": 1,
            "lab_id": "A",
            "lab_name": "Lab A",
            "lab_code": "A",
            "experiment_name": "SEM 觀察",
            "target": 1,
            "created_at": "2026-05-01",
        },
        {
            "id": 2,
            "lab_id": "B",
            "lab_name": "Lab B",
            "lab_code": "B",
            "experiment_name": "光學量測",
            "target": 1,
            "created_at": "2026-05-01",
        },
    ]
    machines = [
        {"lab": "A", "supported_items": ["SEM 觀察"], "utilization": 80},
        {"lab": "B", "supported_items": ["光學量測"], "utilization": 20},
    ]

    assert machine_utilization_score(candidates[0], machines) == 80
    assert machine_utilization_score(candidates[1], machines) == 20
    assert select_dependency_candidate(candidates, machines)["id"] == 2


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


def test_wip_complete_order_guard_allows_any_wip_in_contiguous_same_lab_segment():
    experiments = parse_requested_experiments("Lab A:SEM、Lab A:EDX、Lab B:CV")
    wips = [
        {"id": "a-1", "lab_name": "Lab A", "experiment_item": "SEM", "status": "created"},
        {"id": "a-2", "lab_name": "Lab A", "experiment_item": "EDX", "status": "created"},
        {"id": "b-1", "lab_name": "Lab B", "experiment_item": "CV", "status": "created"},
    ]

    slots = build_ordered_wip_slots(experiments, wips)
    completable_ids = {
        slot["wip"]["id"] for slot in get_completable_wip_slots_for_current_segment(slots)
    }

    assert completable_ids == {"a-1", "a-2"}


def test_wip_complete_order_guard_blocks_same_lab_after_intermediate_lab():
    experiments = parse_requested_experiments("Lab A:SEM、Lab B:CV、Lab A:EDX")
    wips = [
        {"id": "a-1", "lab_name": "Lab A", "experiment_item": "SEM", "status": "created"},
        {"id": "b-1", "lab_name": "Lab B", "experiment_item": "CV", "status": "created"},
        {"id": "a-2", "lab_name": "Lab A", "experiment_item": "EDX", "status": "created"},
    ]

    slots = build_ordered_wip_slots(experiments, wips)
    completable_ids = [
        slot["wip"]["id"] for slot in get_completable_wip_slots_for_current_segment(slots)
    ]

    assert completable_ids == ["a-1"]


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


def test_wip_create_order_guard_allows_aba_implicit_groups():
    sample = {"experiment_item": "Lab A:SEM、Lab B:CV、Lab A:EDX"}

    validate_wip_create_items_in_order(
        sample=sample,
        existing_wips=[],
        requested_items=[
            {"lab_name": "Lab A", "experiment_item": "SEM"},
            {"lab_name": "Lab A", "experiment_item": "EDX"},
        ],
    )


def test_wip_create_order_guard_allows_skip_in_implicit_groups():
    sample = {"experiment_item": "Lab A:SEM、Lab A:EDX、Lab B:CV"}

    validate_wip_create_items_in_order(
        sample=sample,
        existing_wips=[],
        requested_items=[
            {"lab_name": "Lab A", "experiment_item": "EDX"},
        ],
    )


def test_wip_create_order_guard_blocks_skipping_first_contiguous_wip_in_explicit_group():
    sample = {"experiment_item": "G1#1|Lab A:SEM、G1#2|Lab A:EDX、G1#3|Lab B:CV"}

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


def test_wip_owner_lab_visibility_filter_is_strict_for_dispatch_pick_list():
    lab_user = {"role": "lab_supervisor", "lab_name": "Lab A", "department": "Lab A"}
    clauses, params = build_wip_owner_lab_visibility_filter(lab_user)

    assert clauses == ["w.lab_name = :current_lab"]
    assert params == {"current_lab": "Lab A"}

    assert build_wip_owner_lab_visibility_filter({"role": "system_admin"}) == ([], {})

    factory_clauses, factory_params = build_wip_owner_lab_visibility_filter(
        {"role": "plant_user", "name": "王小明"}
    )
    assert factory_clauses == ["1 = 0"]
    assert factory_params == {}

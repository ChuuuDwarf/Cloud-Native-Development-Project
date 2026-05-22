import pytest
from fastapi import HTTPException

from app.services.sample_service import (
    build_sample_visibility_filter,
    can_confirm_pickup,
    can_manage_sample,
    can_view_sample,
    experiment_temp_location,
    get_lab_from_location,
    lab_location,
    machine_location,
    normalize_lab_code,
    receive_location,
    transfer_waiting_location,
    validate_uuid,
)


def test_location_helpers_generate_consistent_lab_areas():
    assert lab_location("Lab A", "收樣區") == "Lab A 收樣區"
    assert lab_location("Lab A 收樣區", "收樣區") == "Lab A 收樣區"
    assert receive_location("Lab B") == "Lab B 收樣區"
    assert experiment_temp_location("Lab C") == "Lab C 實驗暫存區"
    assert machine_location("Lab D") == "Lab D 機台區"
    assert transfer_waiting_location(None) == "交接待送區"


def test_get_lab_from_location_supports_known_labs_only():
    assert get_lab_from_location("Lab A 實驗暫存區") == "Lab A"
    assert get_lab_from_location("Lab B 機台區") == "Lab B"
    assert get_lab_from_location("Warehouse") is None
    assert get_lab_from_location(None) is None


def test_normalize_lab_code_keeps_wip_number_format_stable():
    assert normalize_lab_code("Lab A") == "A"
    assert normalize_lab_code("Lab B") == "B"
    assert normalize_lab_code("特殊實驗室") == "特殊實驗室"
    assert normalize_lab_code(None) == "LAB"


def test_sample_visibility_filter_by_role():
    lab_user = {"role": "lab_staff", "lab_name": "Lab A", "department": "Lab A"}
    clauses, params = build_sample_visibility_filter(lab_user)
    assert clauses == ["s.current_location LIKE :current_lab_prefix"]
    assert params["current_lab_prefix"] == "Lab A%"

    factory_user = {"role": "factory_user", "name": "王小明"}
    clauses, params = build_sample_visibility_filter(factory_user)
    assert clauses == ["s.applicant_name = :applicant_name"]
    assert params == {"applicant_name": "王小明"}

    admin = {"role": "system_admin"}
    assert build_sample_visibility_filter(admin) == ([], {})


def test_sample_scope_all_keeps_related_transferred_samples_visible():
    lab_user = {"role": "lab_supervisor", "lab_name": "Lab A", "department": "Lab A"}
    clauses, params = build_sample_visibility_filter(lab_user, scope="all")

    joined = " ".join(clauses)
    assert "s.current_location LIKE :current_lab_prefix" in joined
    assert "FROM wips w" in joined
    assert "FROM transfers t" in joined
    assert params["current_lab"] == "Lab A"


def test_sample_permissions_match_factory_and_lab_rules():
    sample_in_lab_a = {
        "id": "sample-1",
        "applicant_name": "王小明",
        "status": "outbound",
        "current_location": "Lab A 待取件區",
    }
    lab_a = {"role": "lab_staff", "lab_name": "Lab A", "department": "Lab A"}
    lab_b = {"role": "lab_staff", "lab_name": "Lab B", "department": "Lab B"}
    owner = {"role": "factory_user", "name": "王小明"}
    other_factory = {"role": "factory_user", "name": "陳大華"}

    assert can_view_sample(lab_a, sample_in_lab_a) is True
    assert can_manage_sample(lab_a, sample_in_lab_a) is True
    assert can_view_sample(lab_b, sample_in_lab_a) is False
    assert can_manage_sample(lab_b, sample_in_lab_a) is False
    assert can_view_sample(owner, sample_in_lab_a) is True
    assert can_view_sample(other_factory, sample_in_lab_a) is False
    assert can_confirm_pickup(owner, sample_in_lab_a) is True
    assert can_confirm_pickup(other_factory, sample_in_lab_a) is False


def test_validate_uuid_rejects_invalid_values():
    validate_uuid("11111111-1111-1111-1111-111111111111", "sample_id")

    with pytest.raises(HTTPException) as exc:
        validate_uuid("not-a-uuid", "sample_id")

    assert exc.value.status_code == 400
    assert "sample_id must be a valid UUID" == exc.value.detail

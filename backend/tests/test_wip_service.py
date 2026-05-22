import pytest
from fastapi import HTTPException

from app.services.wip_service import (
    build_wip_visibility_filter,
    can_manage_wip,
    can_view_wip,
    experiment_temp_location,
    lab_location,
    machine_location,
    validate_uuid,
)


def test_wip_location_helpers_match_workflow_locations():
    assert lab_location("Lab A", "實驗暫存區") == "Lab A 實驗暫存區"
    assert machine_location("Lab B") == "Lab B 機台區"
    assert experiment_temp_location("Lab C") == "Lab C 實驗暫存區"


def test_wip_visibility_filter_uses_wip_owner_lab_not_current_location():
    lab_user = {"role": "lab_staff", "lab_name": "Lab A", "department": "Lab A"}
    clauses, params = build_wip_visibility_filter(lab_user)

    assert clauses == ["w.lab_name = :current_lab"]
    assert params == {"current_lab": "Lab A"}


def test_wip_visibility_filter_for_factory_and_admin():
    factory = {"role": "factory_user", "name": "王小明"}
    clauses, params = build_wip_visibility_filter(factory)
    assert clauses == ["s.applicant_name = :applicant_name"]
    assert params == {"applicant_name": "王小明"}

    assert build_wip_visibility_filter({"role": "system_admin"}) == ([], {})


def test_lab_user_can_manage_own_lab_wip_even_after_location_changes():
    wip = {"lab_name": "Lab A", "current_location": "已由使用者取回"}
    lab_a = {"role": "lab_staff", "lab_name": "Lab A", "department": "Lab A"}
    lab_b = {"role": "lab_staff", "lab_name": "Lab B", "department": "Lab B"}

    assert can_view_wip(lab_a, wip) is True
    assert can_manage_wip(lab_a, wip) is True
    assert can_view_wip(lab_b, wip) is False
    assert can_manage_wip(lab_b, wip) is False


def test_factory_user_can_only_view_own_sample_wips():
    wip = {"lab_name": "Lab A"}
    factory = {"role": "factory_user", "name": "王小明"}

    assert can_view_wip(factory, wip, {"applicant_name": "王小明"}) is True
    assert can_view_wip(factory, wip, {"applicant_name": "陳大華"}) is False
    assert can_manage_wip(factory, wip) is False


def test_validate_uuid_rejects_invalid_wip_id():
    validate_uuid("11111111-1111-1111-1111-111111111111", "wip_id")

    with pytest.raises(HTTPException) as exc:
        validate_uuid("bad", "wip_id")

    assert exc.value.status_code == 400
    assert exc.value.detail == "wip_id must be a valid UUID"

import pytest
from fastapi import HTTPException

from app.services.transfer_service import (
    build_transfer_visibility_filter,
    get_user_lab,
    receive_location,
    transfer_waiting_location,
    validate_uuid,
)


def test_transfer_visibility_filter_for_lab_users_includes_incoming_and_outgoing():
    clauses, params = build_transfer_visibility_filter(
        {"role": "lab_staff", "lab_name": "Lab A", "department": "Lab A"}
    )

    assert clauses == ["(from_lab = :current_lab OR to_lab = :current_lab)"]
    assert params == {"current_lab": "Lab A"}


def test_transfer_visibility_filter_blocks_factory_users_and_unknown_roles():
    assert build_transfer_visibility_filter({"role": "factory_user", "name": "王小明"}) == (["1 = 0"], {})
    assert build_transfer_visibility_filter({"role": "guest"}) == (["1 = 0"], {})
    assert build_transfer_visibility_filter({"role": "system_admin"}) == ([], {})


def test_transfer_location_helpers_and_user_lab_fallback():
    assert get_user_lab({"lab_name": None, "department": "Lab B"}) == "Lab B"
    assert transfer_waiting_location("Lab A") == "Lab A 交接待送區"
    assert receive_location("Lab B") == "Lab B 收樣區"


def test_validate_uuid_rejects_bad_transfer_id():
    validate_uuid("11111111-1111-1111-1111-111111111111", "transfer_id")

    with pytest.raises(HTTPException) as exc:
        validate_uuid("bad-transfer", "transfer_id")

    assert exc.value.status_code == 400
    assert exc.value.detail == "transfer_id must be a valid UUID"

"""Tests for the Others helper/service layer (``temporary_others_service``).

This module is a grab-bag of pure string helpers (lab-location naming, lab-code
normalisation, JSON/experiment parsing) plus raw-SQL DB readers over tables that
DO exist in the test schema (``labs`` / ``users`` / ``orders``). Both kinds were
almost entirely uncovered. Pure helpers are tested in isolation; DB helpers run
against ``db_session`` and the seeded corpus.

Note: helpers that read B's ``samples`` table (``generate_sample_no`` etc.) are
out of scope — that table isn't in ``Base.metadata`` so the test schema lacks it.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import temporary_others_service as svc

# NOTE: no module-level ``pytestmark = pytest.mark.asyncio`` — asyncio_mode is
# "auto", so async tests are auto-collected, and a module-level mark would
# wrongly tag the sync pure-helper tests below.


# ---------------------------------------------------------------------------
# Pure helpers (no DB)
# ---------------------------------------------------------------------------


def test_lab_location_appends_area() -> None:
    assert svc.lab_location("材料分析實驗室", "收樣區") == "材料分析實驗室 收樣區"


def test_lab_location_no_double_suffix() -> None:
    # Already ends with the area → returned as-is, not doubled.
    assert svc.lab_location("材料分析實驗室收樣區", "收樣區") == "材料分析實驗室收樣區"


def test_lab_location_none_returns_area() -> None:
    assert svc.lab_location(None, "收樣區") == "收樣區"


def test_named_location_helpers() -> None:
    assert svc.receive_location("LabA") == "LabA 收樣區"
    assert svc.experiment_temp_location("LabA") == "LabA 實驗暫存區"
    assert svc.pickup_location("LabA") == "LabA 待取件區"


def test_normalize_lab_code_from_lab_code_strips_prefix() -> None:
    assert svc.normalize_lab_code_from_lab_code("LAB-A") == "A"
    assert svc.normalize_lab_code_from_lab_code(" lab-bc ") == "BC"


def test_normalize_lab_code_from_lab_code_passthrough_and_none() -> None:
    assert svc.normalize_lab_code_from_lab_code("XYZ") == "XYZ"
    assert svc.normalize_lab_code_from_lab_code(None) is None
    # "LAB-" with nothing after → not stripped (len not > 4).
    assert svc.normalize_lab_code_from_lab_code("LAB-") == "LAB-"


def test_normalize_lab_code_prefix_variants() -> None:
    assert svc.normalize_lab_code("Lab A") == "A"
    assert svc.normalize_lab_code("labB-1") == "B"
    assert svc.normalize_lab_code("LABC") == "C"
    assert svc.normalize_lab_code("labd") == "D"


def test_normalize_lab_code_chinese_map_and_fallback() -> None:
    assert svc.normalize_lab_code("材料分析實驗室") == "A"
    assert svc.normalize_lab_code("電性測試實驗室") == "B"
    assert svc.normalize_lab_code("可靠度實驗室") == "C"
    # Unknown → uppercased passthrough.
    assert svc.normalize_lab_code("foo") == "FOO"
    assert svc.normalize_lab_code(None) == "LAB"


def test_safe_json_loads_variants() -> None:
    assert svc.safe_json_loads(None) is None
    assert svc.safe_json_loads({"a": 1}) == {"a": 1}
    assert svc.safe_json_loads([1, 2]) == [1, 2]
    assert svc.safe_json_loads('{"a": 1}') == {"a": 1}
    assert svc.safe_json_loads("   ") is None
    assert svc.safe_json_loads("not json") is None
    assert svc.safe_json_loads(123) is None


def test_normalize_requested_experiments_extracts_pairs() -> None:
    raw = '[{"lab_name": "LabA", "experiment_item": "SEM"}, {"lab": "LabB", "item": "電性"}]'
    result = svc.normalize_requested_experiments(raw)
    assert result == [
        {"lab_name": "LabA", "experiment_item": "SEM"},
        {"lab_name": "LabB", "experiment_item": "電性"},
    ]


def test_normalize_requested_experiments_skips_incomplete_and_non_dicts() -> None:
    raw = '["nope", {"lab_name": "LabA"}, {"experiment_item": "only"}]'
    assert svc.normalize_requested_experiments(raw) == []


def test_normalize_requested_experiments_non_list_is_empty() -> None:
    assert svc.normalize_requested_experiments('{"lab_name": "LabA"}') == []
    assert svc.normalize_requested_experiments(None) == []


def test_parse_requested_experiments_from_sample() -> None:
    sample = {"experiment_item": "材料分析實驗室:SEM 觀察、電性測試實驗室:光學量測"}
    assert svc.parse_requested_experiments_from_sample(sample) == [
        {"lab_name": "材料分析實驗室", "experiment_item": "SEM 觀察"},
        {"lab_name": "電性測試實驗室", "experiment_item": "光學量測"},
    ]


def test_parse_requested_experiments_skips_malformed_parts() -> None:
    sample = {"experiment_item": "no-colon-here、:emptyLab、LabA:"}
    assert svc.parse_requested_experiments_from_sample(sample) == []


def test_parse_requested_experiments_empty_sample() -> None:
    assert svc.parse_requested_experiments_from_sample({}) == []


def test_removed_endpoint_response_raises_410() -> None:
    with pytest.raises(HTTPException) as exc:
        svc.removed_endpoint_response("old endpoint")
    assert exc.value.status_code == 410


# ---------------------------------------------------------------------------
# DB readers (run against the seeded test schema)
# ---------------------------------------------------------------------------


async def test_get_real_labs_returns_active_labs(db_session: AsyncSession) -> None:
    labs = await svc.get_real_labs(db_session)
    assert labs, "seed corpus should have at least one active lab"
    codes = {lab["code"] for lab in labs}
    assert "LAB-A" in codes
    # All returned labs are active.
    assert all(lab["is_active"] for lab in labs)


async def test_get_generated_storage_locations_three_areas_per_lab(
    db_session: AsyncSession,
) -> None:
    labs = await svc.get_real_labs(db_session)
    locations = await svc.get_generated_storage_locations(db_session)
    assert len(locations) == 3 * len(labs)
    areas = {loc["area"] for loc in locations}
    assert areas == {"收樣區", "實驗暫存區", "待取件區"}
    # Codes are uppercased area suffixes on the lab code.
    assert any(loc["code"].endswith("-RECEIVE") for loc in locations)


async def test_get_real_users_falls_back_when_department_column_missing(
    db_session: AsyncSession,
) -> None:
    """The primary query references ``u.department`` (which doesn't exist —
    the column is ``department_id``), so this exercises the except/rollback
    fallback that does ``SELECT *``. Either way we get rows back."""
    users = await svc.get_real_users(db_session)
    assert users, "seed corpus should have users"
    emails = {u.get("email") for u in users}
    assert "admin@example.com" in emails


async def test_get_real_orders_and_get_real_order(db_session: AsyncSession) -> None:
    import uuid
    from datetime import UTC, datetime

    from app.db.models.order_management import OrderModel

    order_no = f"OTH-{uuid.uuid4().hex[:8]}"
    order = OrderModel(
        order_no=order_no,
        applicant_id="oth-applicant",
        department_id="DEPT-RD",
        apply_date=datetime.now(UTC),
        status="draft",
        priority="normal",
        total_items=1,
    )
    db_session.add(order)
    await db_session.commit()

    orders = await svc.get_real_orders(db_session)
    assert any(o["order_no"] == order_no for o in orders)

    by_no = await svc.get_real_order(db_session, order_no)
    assert by_no is not None
    assert by_no["order_no"] == order_no
    # Resolve by stringified id too.
    by_id = await svc.get_real_order(db_session, str(order.id))
    assert by_id is not None
    assert by_id["id"] == order.id


async def test_get_real_order_missing_returns_none(db_session: AsyncSession) -> None:
    assert await svc.get_real_order(db_session, "NO-SUCH-ORDER-xyz") is None


async def test_resolve_real_lab_name_by_code(db_session: AsyncSession) -> None:
    assert await svc.resolve_real_lab_name(db_session, "LAB-A") == "材料分析實驗室"


async def test_resolve_real_lab_name_unknown_returns_input(db_session: AsyncSession) -> None:
    # Unknown lab value → returns the original value unchanged (legacy safety).
    assert await svc.resolve_real_lab_name(db_session, "ghost-lab") == "ghost-lab"


async def test_resolve_real_lab_name_none(db_session: AsyncSession) -> None:
    assert await svc.resolve_real_lab_name(db_session, None) is None


async def test_resolve_lab_code_from_db(db_session: AsyncSession) -> None:
    # Resolves via the labs table, then normalizes "LAB-A" → "A".
    assert await svc.resolve_lab_code(db_session, "材料分析實驗室") == "A"


async def test_resolve_lab_code_none_defaults(db_session: AsyncSession) -> None:
    assert await svc.resolve_lab_code(db_session, None) == "LAB"


async def test_resolve_lab_code_unknown_falls_back_to_string_rule(
    db_session: AsyncSession,
) -> None:
    # Not in DB → falls through to normalize_lab_code's string heuristics.
    assert await svc.resolve_lab_code(db_session, "材料分析實驗室x") == "材料分析實驗室X".upper()


async def test_resolve_current_user_fallback_without_headers(
    db_session: AsyncSession,
) -> None:
    """With no request/headers, returns the most-recent seeded user (or the
    safe system fallback). Either way it's a dict with the expected keys."""
    result = await svc.resolve_current_user(db_session, request=None)
    assert isinstance(result, dict)
    # Both the DB-row path (SELECT u.*) and the safe fallback carry id + email.
    assert "id" in result
    assert "email" in result

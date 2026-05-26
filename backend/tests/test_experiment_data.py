"""Unit tests for D's experiment-execution data handling (this session's work).

- Machine completion / result upload persists measured ``experiment_data`` once,
  so it can be shown at 驗證數據 and reused by the report (no re-randomising).
- The background auto-progress cadence stays within the ~30s demo budget.
"""

import math

from app.db.models import Wip, WipExecution
from app.modules.experiment_runs.service import (
    PROGRESS_STEP_PERCENT,
    PROGRESS_TICK_SECONDS,
    _ensure_experiment_data,
)
from app.modules.reports.fake_data import generate_for_items


def test_ensure_experiment_data_generates_for_wip_item() -> None:
    wip = Wip(wip_no="W1", order_no="O1", experiment_item="EDX")
    exec_row = WipExecution(wip_no="W1")

    _ensure_experiment_data(wip, exec_row)

    assert exec_row.experiment_data
    assert "EDX" in exec_row.experiment_data
    assert exec_row.experiment_data["EDX"]  # non-empty measurement fields


def test_ensure_experiment_data_does_not_overwrite_existing() -> None:
    existing = {"EDX": {"Si 含量": "60 %"}}
    wip = Wip(wip_no="W1", order_no="O1", experiment_item="EDX")
    exec_row = WipExecution(wip_no="W1", experiment_data=existing)

    _ensure_experiment_data(wip, exec_row)

    assert exec_row.experiment_data is existing  # verified data kept intact


def test_ensure_experiment_data_handles_missing_item() -> None:
    wip = Wip(wip_no="W1", order_no="O1", experiment_item=None)
    exec_row = WipExecution(wip_no="W1")

    _ensure_experiment_data(wip, exec_row)

    assert exec_row.experiment_data == {}


def test_auto_progress_completes_within_demo_budget() -> None:
    ticks = math.ceil(100 / PROGRESS_STEP_PERCENT)
    assert ticks * PROGRESS_TICK_SECONDS <= 30


def test_generate_for_items_shape() -> None:
    data = generate_for_items(["EDX"])
    assert set(data) == {"EDX"}
    assert isinstance(data["EDX"], dict) and data["EDX"]

    assert generate_for_items([]) == {}
    assert generate_for_items([""]) == {}  # falsy items are skipped

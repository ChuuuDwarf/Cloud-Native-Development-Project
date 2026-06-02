"""Unit tests for D's experiment-execution data handling (this session's work).

- Machine completion / result upload persists measured ``experiment_data`` once,
  so it can be shown at 驗證數據 and reused by the report (no re-randomising).
- The background auto-progress cadence stays within the ~30s demo budget.
"""

import math

import pytest

from app.db.models import Wip, WipExecution
from app.modules.experiment_runs.service import (
    PROGRESS_STEP_PERCENT,
    PROGRESS_TICK_SECONDS,
    _ensure_experiment_data,
)
from app.modules.reports.fake_data import (
    generate_experiment_data,
    generate_for_items,
)


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


# Expected measurement-field keys per experiment item. Exercising every entry
# drives the corresponding ``_rng.*`` generator line so demo-data stays covered.
EXPERIMENT_FIELD_KEYS = {
    "EDX": {"Si 含量", "O 含量", "Al 含量", "其他元素", "加速電壓"},
    "FIB": {"切割深度", "研磨時間", "離子束電流"},
    "SEM": {"放大倍率", "解析度", "加速電壓", "影像張數"},
    "CV": {"平帶電壓 Vfb", "最大電容 Cmax", "最小電容 Cmin", "界面態密度 Dit"},
    "IV": {"閾值電壓 Vth", "導通電流 Ion", "關斷電流 Ioff", "漏電流"},
    "Probe": {"接觸電阻", "片電阻", "量測點數"},
    "ESD": {"HBM 通過電壓", "MM 通過電壓", "CDM 通過電壓", "判定"},
    "HTOL": {"測試時數", "樣品數", "失效數", "FIT"},
    "TC": {"溫度範圍", "循環數", "失效數", "分層比例"},
}


@pytest.mark.parametrize("item", sorted(EXPERIMENT_FIELD_KEYS))
def test_generate_experiment_data_returns_expected_fields(item: str) -> None:
    data = generate_experiment_data(item)

    assert set(data) == EXPERIMENT_FIELD_KEYS[item]
    assert all(isinstance(v, str) and v for v in data.values())


def test_generate_experiment_data_unknown_item_uses_generic_fallback() -> None:
    data = generate_experiment_data("not-a-real-item")

    assert set(data) == {"量測值", "標準差", "樣本數"}
    assert all(isinstance(v, str) and v for v in data.values())


def test_generate_for_items_covers_all_known_types_plus_unknown() -> None:
    items = [*sorted(EXPERIMENT_FIELD_KEYS), "unknown"]
    data = generate_for_items(items)

    assert set(data) == set(items)
    for item in EXPERIMENT_FIELD_KEYS:
        assert set(data[item]) == EXPERIMENT_FIELD_KEYS[item]
    assert set(data["unknown"]) == {"量測值", "標準差", "樣本數"}

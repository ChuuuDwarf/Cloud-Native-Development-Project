import pytest
from pydantic import ValidationError

from schemas import (
    AssignRequest,
    DispatchCreate,
    MachineCreate,
    MachineStatusUpdate,
    MachineUpdate,
    RecipeCreate,
    ReplanRequest,
    SuggestRequest,
)


def test_machine_create_defaults_status_related_fields():
    payload = MachineCreate(
        machineId="AFM-004",
        name="原子力顯微鏡",
        lab="LAB A",
        supportedItems=["表面形貌分析"],
        owner="林育誠",
    )

    assert payload.utilization == 0
    assert payload.lastMaintenance == "尚未保養"


@pytest.mark.parametrize("model", [MachineCreate, MachineUpdate])
def test_machine_utilization_must_be_between_zero_and_one_hundred(model):
    data = {
        "name": "機台",
        "lab": "LAB A",
        "supportedItems": ["材料成份分析"],
        "owner": "林育誠",
        "utilization": 101,
        "lastMaintenance": "2026-05-20",
    }
    if model is MachineCreate:
        data["machineId"] = "M-001"

    with pytest.raises(ValidationError):
        model(**data)


def test_machine_status_update_accepts_only_known_status():
    assert MachineStatusUpdate(status="故障中").status == "故障中"

    with pytest.raises(ValidationError):
        MachineStatusUpdate(status="未知")


def test_recipe_create_defaults_parameters_to_empty_dict():
    payload = RecipeCreate(
        recipeId="RCP-001",
        name="標準流程",
        version="v1.0",
        experimentItem="材料成份分析",
        machineIds=["TEM-001"],
        method="EDS mapping",
        updatedBy="林育誠",
    )

    assert payload.parameters == {}


def test_dispatch_create_allows_backend_to_fill_lab():
    payload = DispatchCreate(
        dispatchId="DSP-100",
        wipId="WIP-100",
        orderId="WO-100",
        experimentItem="材料成份分析",
        priority="高",
        dueAt="2026-05-24 12:00",
    )

    assert payload.lab is None


def test_suggest_request_defaults_to_fifo():
    assert SuggestRequest().strategy == "FIFO"


def test_suggest_request_rejects_unknown_strategy():
    with pytest.raises(ValidationError):
        SuggestRequest(strategy="Random")


def test_replan_request_defaults_to_hybrid():
    payload = ReplanRequest(reason="人員不足重排")

    assert payload.strategy == "Hybrid"


def test_assign_request_keeps_schedule_fields():
    payload = AssignRequest(
        machineId="TEM-001",
        recipeId="RCP-TEM-001",
        scheduledStart="2026-05-24 09:00",
        scheduledEnd="2026-05-24 11:00",
    )

    assert payload.machineId == "TEM-001"
    assert payload.scheduledEnd == "2026-05-24 11:00"

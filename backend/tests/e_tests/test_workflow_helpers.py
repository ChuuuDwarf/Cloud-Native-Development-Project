from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.services import workflow_helpers as wh


class Row:
    def __init__(self, **values: object) -> None:
        self._mapping = values


class Result:
    def __init__(self, rows: list[Row] | None = None) -> None:
        self.rows = rows or []

    def __iter__(self):
        return iter(self.rows)

    def fetchone(self):
        return self.rows[0] if self.rows else None


class FakeDb:
    def __init__(self, results: list[Result]) -> None:
        self.results = results
        self.calls: list[dict | None] = []
        self.rollbacks = 0

    async def execute(self, _stmt: object, params: dict | None = None) -> Result:
        self.calls.append(params)
        if not self.results:
            return Result()
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    async def rollback(self) -> None:
        self.rollbacks += 1


def test_location_and_lab_code_helpers() -> None:
    assert wh.lab_location(None, "收樣區") == "收樣區"
    assert wh.lab_location("材料分析實驗室", "收樣區") == "材料分析實驗室 收樣區"
    assert wh.lab_location("材料分析實驗室 收樣區", "收樣區") == "材料分析實驗室 收樣區"
    assert wh.receive_location("材料分析實驗室") == "材料分析實驗室 收樣區"
    assert wh.experiment_temp_location("材料分析實驗室") == "材料分析實驗室 實驗暫存區"
    assert wh.pickup_location("材料分析實驗室") == "材料分析實驗室 待取件區"

    assert wh.normalize_lab_code_from_lab_code(None) is None
    assert wh.normalize_lab_code_from_lab_code(" lab-a ") == "A"
    assert wh.normalize_lab_code_from_lab_code("abc") == "ABC"
    assert wh.normalize_lab_code(None) == "LAB"
    assert wh.normalize_lab_code("LabB") == "B"
    assert wh.normalize_lab_code("可靠度實驗室") == "C"
    assert wh.normalize_lab_code("其他實驗室") == "其他實驗室"


def test_json_and_requested_experiment_parsing() -> None:
    assert wh.safe_json_loads(None) is None
    assert wh.safe_json_loads({"a": 1}) == {"a": 1}
    assert wh.safe_json_loads("") is None
    assert wh.safe_json_loads("{bad") is None
    assert wh.safe_json_loads(123) is None

    value = '[{"lab":"材料分析實驗室","item":"SEM"},{"target_lab":"電性測試實驗室","name":"IV"}, 1]'
    assert wh.normalize_requested_experiments(value) == [
        {"lab_name": "材料分析實驗室", "experiment_item": "SEM"},
        {"lab_name": "電性測試實驗室", "experiment_item": "IV"},
    ]
    assert wh.normalize_requested_experiments({"not": "a list"}) == []
    assert wh.parse_requested_experiments_from_sample(
        {"experiment_item": "材料分析實驗室:SEM、bad、電性測試實驗室:IV"}
    ) == [
        {"lab_name": "材料分析實驗室", "experiment_item": "SEM"},
        {"lab_name": "電性測試實驗室", "experiment_item": "IV"},
    ]


async def test_generated_storage_locations_from_real_labs() -> None:
    db = FakeDb(
        [
            Result(
                [
                    Row(
                        id="lab-1",
                        code="LAB-A",
                        name="材料分析實驗室",
                        capacity=5,
                        is_active=True,
                        created_at=None,
                        updated_at=None,
                    )
                ]
            )
        ]
    )

    locations = await wh.get_generated_storage_locations(db)  # type: ignore[arg-type]

    assert [loc["area"] for loc in locations] == ["收樣區", "實驗暫存區", "待取件區"]
    assert locations[0]["code"] == "LAB-A-RECEIVE"


async def test_get_real_users_falls_back_after_join_query_failure() -> None:
    db = FakeDb([RuntimeError("no lab_id"), Result([Row(id="u-1", name="Alice")])])

    users = await wh.get_real_users(db)  # type: ignore[arg-type]

    assert users == [{"id": "u-1", "name": "Alice"}]
    assert db.rollbacks == 1


async def test_resolve_current_user_uses_headers_row_or_fallback() -> None:
    request = type(
        "Req",
        (),
        {"headers": {"x-user-id": "u-1", "x-user-email": "a@example.com", "x-user-name": "A"}},
    )()
    db = FakeDb([Result([Row(id="u-1", name="Alice", email="a@example.com")])])

    assert (await wh.resolve_current_user(db, request))["name"] == "Alice"  # type: ignore[arg-type]

    fallback_db = FakeDb([RuntimeError("db down")])
    fallback = await wh.resolve_current_user(fallback_db, request)  # type: ignore[arg-type]
    assert fallback["id"] == "u-1"
    assert fallback["role"] == "system_admin"
    assert fallback_db.rollbacks == 1


async def test_real_order_and_lab_resolution_helpers() -> None:
    assert await wh.get_real_order(FakeDb([Result()]), "ORD-1") is None  # type: ignore[arg-type]
    assert (await wh.get_real_order(FakeDb([Result([Row(order_no="ORD-1")])]), "ORD-1")) == {
        "order_no": "ORD-1"
    }
    assert await wh.resolve_real_lab_name(FakeDb([]), None) is None  # type: ignore[arg-type]
    assert await wh.resolve_real_lab_name(FakeDb([Result()]), "legacy") == "legacy"  # type: ignore[arg-type]
    assert (
        await wh.resolve_real_lab_name(
            FakeDb([Result([Row(name="材料分析實驗室")])]),
            "LAB-A",  # type: ignore[arg-type]
        )
        == "材料分析實驗室"
    )


async def test_sample_and_wip_number_generation() -> None:
    sample_db = FakeDb([Result([Row(total=1)]), Result([Row(exists=1)]), Result()])
    assert await wh.generate_sample_no(sample_db) == "SMP-2026-0003"  # type: ignore[arg-type]

    with pytest.raises(RuntimeError):
        await wh.generate_sample_no(FakeDb([Result()]))  # type: ignore[arg-type]

    lab_db = FakeDb([Result([Row(code="LAB-A")]), Result([Row(exists=1)]), Result()])
    assert (
        await wh.generate_unique_wip_no(
            lab_db,
            "SMP-2026-0001",
            1,
            "材料分析實驗室",  # type: ignore[arg-type]
        )
        == "WIP-2026-0001-A-02"
    )


async def test_generation_raises_when_candidates_are_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("builtins.range", lambda *_args: [1])

    with pytest.raises(HTTPException):
        await wh.generate_sample_no(FakeDb([Result([Row(total=0)]), Result([Row(exists=1)])]))  # type: ignore[arg-type]
    with pytest.raises(HTTPException):
        await wh.generate_unique_wip_no(
            FakeDb([Result(), Result([Row(exists=1)])]),
            "SMP-2026-0001",
            1,
            "LAB-A",  # type: ignore[arg-type]
        )

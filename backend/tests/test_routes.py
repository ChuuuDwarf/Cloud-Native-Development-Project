from datetime import datetime

import pytest
from fastapi import HTTPException
from routers import health, machines, recipes
from schemas import MachineCreate, MachineStatusUpdate, RecipeCreate, User


def user(role="實驗室人員", lab="LAB A"):
    return User(
        userId="u-lab-a",
        name="林育誠",
        role=role,
        department="實驗室",
        lab=lab,
    )


class _Result:
    def __init__(self, row=None, rows=None):
        self.row = row
        self.rows = rows or []

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows


class _Conn:
    def __init__(self, results=None):
        self.results = list(results or [])
        self.queries = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, query, params=()):
        self.queries.append((query, params))
        if self.results:
            return self.results.pop(0)
        return _Result()


def machine_row(machine_id="TEM-001", lab="LAB A", status="閒置"):
    return {
        "machine_id": machine_id,
        "name": "穿透式電子顯微鏡",
        "lab": lab,
        "status": status,
        "supported_items": ["材料成份分析"],
        "utilization": 20,
        "owner": "林育誠",
        "last_maintenance": "2026-05-10",
    }


def recipe_row(recipe_id="RCP-001"):
    return {
        "recipe_id": recipe_id,
        "name": "TEM 標準流程",
        "version": "v1.0",
        "experiment_item": "材料成份分析",
        "machine_ids": ["TEM-001"],
        "method": "EDS mapping",
        "parameters": {"voltage": "200kV"},
        "updated_by": "林育誠",
        "updated_at": datetime(2026, 5, 23, 9, 30),
    }


def test_health_check_executes_database_probe(monkeypatch):
    conn = _Conn()
    monkeypatch.setattr(health, "get_connection", lambda: conn)

    assert health.health_check() == {"status": "ok", "database": "connected"}
    assert conn.queries[0][0] == "SELECT 1"


def test_get_machines_filters_by_current_user_lab(monkeypatch):
    conn = _Conn(results=[_Result(rows=[machine_row(), machine_row("SEM-001")])])
    monkeypatch.setattr(machines, "get_connection", lambda: conn)
    monkeypatch.setattr(machines, "get_user", lambda _conn, _user_id: user())

    payload = machines.get_machines(x_user_id="u-lab-a")

    assert payload["total"] == 2
    assert conn.queries[0][1] == ("LAB A",)
    assert [item.machineId for item in payload["data"]] == ["TEM-001", "SEM-001"]


def test_create_machine_inserts_idle_machine(monkeypatch):
    conn = _Conn(results=[_Result(row=machine_row("AFM-004"))])
    monkeypatch.setattr(machines, "get_connection", lambda: conn)
    monkeypatch.setattr(machines, "get_user", lambda _conn, _user_id: user())

    payload = MachineCreate(
        machineId="AFM-004",
        name="原子力顯微鏡",
        lab="LAB A",
        supportedItems=["表面形貌分析"],
        owner="林育誠",
        utilization=18,
        lastMaintenance="2026-05-20",
    )

    result = machines.create_machine(payload, x_user_id="u-lab-a")

    assert result["message"] == "machine created"
    assert result["data"].machineId == "AFM-004"
    assert conn.queries[0][1][3] == ["表面形貌分析"]


def test_update_machine_status_returns_404_for_missing_machine(monkeypatch):
    conn = _Conn(results=[_Result(row=None)])
    monkeypatch.setattr(machines, "get_connection", lambda: conn)
    monkeypatch.setattr(machines, "get_user", lambda _conn, _user_id: user())

    with pytest.raises(HTTPException) as exc:
        machines.update_machine_status(
            "missing",
            MachineStatusUpdate(status="使用中"),
            x_user_id="u-lab-a",
        )

    assert exc.value.status_code == 404


def test_update_machine_status_updates_existing_machine(monkeypatch):
    conn = _Conn(
        results=[
            _Result(row=machine_row()),
            _Result(row=machine_row(status="使用中")),
        ]
    )
    monkeypatch.setattr(machines, "get_connection", lambda: conn)
    monkeypatch.setattr(machines, "get_user", lambda _conn, _user_id: user())

    result = machines.update_machine_status(
        "TEM-001",
        MachineStatusUpdate(status="使用中"),
        x_user_id="u-lab-a",
    )

    assert result["message"] == "machine status updated"
    assert result["data"].status == "使用中"
    assert conn.queries[1][1] == ("使用中", "TEM-001")


def test_get_recipes_for_global_user_does_not_lab_filter(monkeypatch):
    conn = _Conn(results=[_Result(rows=[recipe_row()])])
    monkeypatch.setattr(recipes, "get_connection", lambda: conn)
    monkeypatch.setattr(
        recipes,
        "get_user",
        lambda _conn, _user_id: user(role="系統管理者", lab=None),
    )

    payload = recipes.get_recipes(x_user_id="u-admin")

    assert payload["total"] == 1
    assert "JOIN machines" not in conn.queries[0][0]


def test_create_recipe_requires_all_machines_in_user_lab(monkeypatch):
    conn = _Conn(results=[_Result(row={"count": 0})])
    monkeypatch.setattr(recipes, "get_connection", lambda: conn)
    monkeypatch.setattr(recipes, "get_user", lambda _conn, _user_id: user())
    payload = RecipeCreate(
        recipeId="RCP-404",
        name="不存在機台流程",
        version="v1.0",
        experimentItem="材料成份分析",
        machineIds=["NOPE"],
        method="test",
        updatedBy="林育誠",
    )

    with pytest.raises(HTTPException) as exc:
        recipes.create_recipe(payload, x_user_id="u-lab-a")

    assert exc.value.status_code == 400
    assert exc.value.detail == "Some machines do not exist"


def test_create_recipe_uses_current_user_as_updated_by(monkeypatch):
    conn = _Conn(results=[_Result(row={"count": 1}), _Result(row=recipe_row())])
    monkeypatch.setattr(recipes, "get_connection", lambda: conn)
    monkeypatch.setattr(recipes, "get_user", lambda _conn, _user_id: user())
    payload = RecipeCreate(
        recipeId="RCP-001",
        name="TEM 標準流程",
        version="v1.0",
        experimentItem="材料成份分析",
        machineIds=["TEM-001"],
        method="EDS mapping",
        parameters={"voltage": "200kV"},
        updatedBy="前端傳入者",
    )

    result = recipes.create_recipe(payload, x_user_id="u-lab-a")

    assert result["message"] == "recipe created"
    assert conn.queries[1][1][7] == "林育誠"

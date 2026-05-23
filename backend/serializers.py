from typing import Any

from schemas import Dispatch, Machine, Recipe, User


def response(data: object, message: str = "success") -> dict[str, object]:
    return {"data": data, "message": message}


def list_response(data: list[object], message: str = "success") -> dict[str, object]:
    return {"data": data, "total": len(data), "message": message}


def machine_from_row(row: dict[str, Any]) -> Machine:
    return Machine(
        machineId=str(row["machine_id"]),
        name=str(row["name"]),
        lab=str(row["lab"]),
        status=row["status"],
        supportedItems=list(row["supported_items"]),
        utilization=int(row["utilization"]),
        owner=str(row["owner"]),
        lastMaintenance=str(row["last_maintenance"]),
    )


def user_from_row(row: dict[str, Any]) -> User:
    return User(
        userId=str(row["user_id"]),
        name=str(row["name"]),
        role=row["role"],
        department=str(row["department"]),
        lab=row["lab"],
    )


def recipe_from_row(row: dict[str, Any]) -> Recipe:
    return Recipe(
        recipeId=str(row["recipe_id"]),
        name=str(row["name"]),
        version=str(row["version"]),
        experimentItem=str(row["experiment_item"]),
        machineIds=list(row["machine_ids"]),
        method=str(row["method"]),
        parameters=dict(row["parameters"]),
        updatedBy=str(row["updated_by"]),
        updatedAt=row["updated_at"].strftime("%Y-%m-%d %H:%M"),
    )


def dispatch_from_row(row: dict[str, Any]) -> Dispatch:
    return Dispatch(
        dispatchId=str(row["dispatch_id"]),
        wipId=str(row["wip_id"]),
        orderId=str(row["order_id"]),
        experimentItem=str(row["experiment_item"]),
        priority=str(row["priority"]),
        lab=str(row["lab"]),
        dueAt=str(row["due_at"]),
        status=row["status"],
        suggestedMachineId=row["suggested_machine_id"],
        assignedMachineId=row["assigned_machine_id"],
        assignedRecipeId=row["assigned_recipe_id"],
        scheduledStart=row["scheduled_start"],
        scheduledEnd=row["scheduled_end"],
        createdBy=row["created_by"],
        assignedBy=row["assigned_by"],
        strategy=row["strategy"],
        replanReason=row["replan_reason"],
    )

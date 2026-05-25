"""camelCase serializer for dispatch responses. Output matches the frontend
``Dispatch`` contract (``frontend/src/types/dispatches.ts``)."""

from __future__ import annotations

from app.db.models import Dispatch


def dispatch_dict(d: Dispatch) -> dict:
    return {
        "dispatchId": d.dispatch_id,
        "wipId": d.wip_id,
        "orderId": d.order_id,
        "experimentItem": d.experiment_item,
        "priority": d.priority,
        "lab": d.lab,
        "dueAt": d.due_at,
        "status": d.status,
        "suggestedMachineId": d.suggested_machine_id,
        "assignedMachineId": d.assigned_machine_id,
        "assignedRecipeId": d.assigned_recipe_id,
        "scheduledStart": d.scheduled_start,
        "scheduledEnd": d.scheduled_end,
        "createdBy": d.created_by,
        "assignedBy": d.assigned_by,
        "strategy": d.strategy,
        "replanReason": d.replan_reason,
    }

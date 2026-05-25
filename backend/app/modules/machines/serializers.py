"""camelCase serializer for machine responses. Output matches the frontend
``Machine`` contract (``frontend/src/types/machines.ts``)."""

from __future__ import annotations

from app.db.models import Machine


def machine_dict(m: Machine) -> dict:
    return {
        "machineId": m.machine_id,
        "name": m.name,
        "lab": m.lab,
        "status": m.status,
        "supportedItems": list(m.supported_items or []),
        "utilization": m.utilization,
        "owner": m.owner,
        "lastMaintenance": m.last_maintenance,
    }

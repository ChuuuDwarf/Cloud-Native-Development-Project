"""HTTP routes for /api/experiment-runs. Owned by 組員 D."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/experiment-runs", tags=["ExperimentRuns"])


@router.get("")
async def list_experiment_runs() -> dict:
    return {
        "items": [],
        "total": 0,
        "message": "組員 D: implement experiment-runs module",
    }

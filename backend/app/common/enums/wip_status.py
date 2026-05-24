from enum import StrEnum


class WipStatus(StrEnum):
    CREATED = "created"
    WAITING_DISPATCH = "waiting_dispatch"
    IN_SCHEDULE = "in_schedule"
    WAITING_LOAD = "waiting_load"
    RUNNING = "running"
    UNLOADED = "unloaded"
    WAITING_CONFIRM = "waiting_confirm"
    COMPLETED = "completed"
    TERMINATED = "terminated"

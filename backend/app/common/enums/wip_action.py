from enum import StrEnum


class WipAction(StrEnum):
    DISPATCH = "dispatch"
    SCHEDULE = "schedule"
    LOAD = "load"
    UNLOAD = "unload"
    CONFIRM = "confirm"
    TERMINATE = "terminate"
    REOPEN = "reopen"

from enum import Enum


class WipAction(str, Enum):
    DISPATCH = "dispatch"
    SCHEDULE = "schedule"
    LOAD = "load"
    UNLOAD = "unload"
    CONFIRM = "confirm"
    TERMINATE = "terminate"
    REOPEN = "reopen"

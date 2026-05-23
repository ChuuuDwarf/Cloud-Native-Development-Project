from enum import StrEnum


class AuditTargetType(StrEnum):
    ORDER = "order"
    SAMPLE = "sample"
    WIP = "wip"
    MACHINE = "machine"
    RECIPE = "recipe"
    SCHEDULE = "schedule"
    DISPATCH = "dispatch"
    EXPERIMENT_RUN = "experiment_run"
    REPORT = "report"
    ISSUE = "issue"
    NOTIFICATION = "notification"
    USER = "user"
    ROLE = "role"
    LAB = "lab"
    DEPARTMENT = "department"
    STORAGE_LOCATION = "storage_location"
    SYSTEM_SETTING = "system_setting"
    FILE = "file"

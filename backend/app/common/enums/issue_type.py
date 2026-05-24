from enum import StrEnum


class IssueType(StrEnum):
    ABNORMAL = "abnormal"
    WARNING = "warning"
    TERMINATION_REQUEST = "termination_request"

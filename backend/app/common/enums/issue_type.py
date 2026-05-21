from enum import Enum


class IssueType(str, Enum):
    ABNORMAL = "abnormal"
    WARNING = "warning"
    TERMINATION_REQUEST = "termination_request"

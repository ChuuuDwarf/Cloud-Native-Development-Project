from enum import Enum


class IssueAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    CLOSE = "close"
    ESCALATE = "escalate"
    ASSIGN = "assign"
    REOPEN = "reopen"

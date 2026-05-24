from enum import StrEnum


class IssueAction(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    CLOSE = "close"
    ESCALATE = "escalate"
    ASSIGN = "assign"
    REOPEN = "reopen"

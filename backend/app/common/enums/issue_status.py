from enum import StrEnum


class IssueStatus(StrEnum):
    OPEN = "open"
    ASSIGNED = "assigned"
    ESCALATED = "escalated"
    CLOSED = "closed"

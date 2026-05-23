from enum import Enum


class IssueStatus(str, Enum):
    OPEN = "open"
    ASSIGNED = "assigned"
    ESCALATED = "escalated"
    CLOSED = "closed"

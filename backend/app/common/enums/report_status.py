from enum import StrEnum


class ReportStatus(StrEnum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    CONFIRMED = "confirmed"
    PUBLISHED = "published"
    RETURNED = "returned"
    REVISED = "revised"

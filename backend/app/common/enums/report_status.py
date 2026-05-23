from enum import Enum


class ReportStatus(str, Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    CONFIRMED = "confirmed"
    PUBLISHED = "published"
    RETURNED = "returned"
    REVISED = "revised"

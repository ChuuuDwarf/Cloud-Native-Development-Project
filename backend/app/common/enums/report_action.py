from enum import StrEnum


class ReportAction(StrEnum):
    SUBMIT_REVIEW = "submit_review"
    APPROVE = "approve"
    REJECT = "reject"
    PUBLISH = "publish"
    RETURN_TO_USER = "return_to_user"
    CREATE_REVISION = "create_revision"

"""Domain HTTPException subclasses.

Each carries a stable ``code`` for the ``ErrorResponse.error.code`` field
so the frontend can map errors to user-facing messages.
"""

from fastapi import HTTPException, status


class AppError(HTTPException):
    code: str = "INTERNAL_ERROR"
    default_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, message: str | None = None, status_code: int | None = None) -> None:
        super().__init__(
            status_code=status_code or self.default_status,
            detail=message or self.code,
        )


class ValidationError(AppError):
    code = "VALIDATION_ERROR"
    default_status = status.HTTP_422_UNPROCESSABLE_ENTITY


class NotFoundError(AppError):
    code = "NOT_FOUND"
    default_status = status.HTTP_404_NOT_FOUND


class UnauthorizedError(AppError):
    code = "UNAUTHORIZED"
    default_status = status.HTTP_401_UNAUTHORIZED


class ForbiddenError(AppError):
    code = "FORBIDDEN"
    default_status = status.HTTP_403_FORBIDDEN


class ConflictError(AppError):
    code = "CONFLICT"
    default_status = status.HTTP_409_CONFLICT


class IllegalStateError(AppError):
    code = "ILLEGAL_STATE"
    default_status = status.HTTP_409_CONFLICT

"""Pydantic request DTOs for the closures module.

JSON fields use camelCase (development_standards.md §6.3). Response bodies are
plain dicts produced by the serializers + service, wrapped by the shared
``ApiResponse`` / ``PageResponse`` envelopes in the router.
"""

from pydantic import BaseModel, Field


class CloseStepBody(BaseModel):
    """結單流程操作（入庫 / 出庫 / 結案）共用備註。

    Ported verbatim from Role D's ``app/schemas.py::CloseStepBody``.
    """

    operator: str | None = Field(default=None, description="操作人")
    note: str | None = Field(default=None, description="備註")

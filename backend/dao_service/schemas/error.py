"""Error response schema following RFC 7807 Problem Details."""

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Standard error response structure."""

    type: str
    title: str
    status: int
    detail: str
    instance: str

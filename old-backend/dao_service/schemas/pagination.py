"""Generic pagination response wrapper."""

from typing import Generic, List, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Consistent pagination envelope for all list endpoints."""

    items: List[T]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool

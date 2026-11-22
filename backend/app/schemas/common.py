from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard pagination envelope (docs/05-API.md section 2.1)."""
    items: List[T] = Field(default_factory=list, description="Page of items")
    total: int = Field(0, description="Total matching items in collection")
    limit: int = Field(20, description="Page size limit")
    offset: int = Field(0, description="Starting record offset")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None


class StandardErrorResponse(BaseModel):
    """Standard error envelope matching frontend and API contracts (docs/05-API.md section 2.2)."""
    error_code: str
    detail: str
    error: ErrorDetail

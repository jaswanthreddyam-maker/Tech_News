from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

# Generic Types
T = TypeVar("T")


class PaginationMetadata(BaseModel):
    next_cursor: str | None = Field(None, description="Cursor token for the next page of results")
    has_more: bool = Field(False, description="Flag indicating if more results are available")
    limit: int = Field(20, description="Number of results fetched")


class BaseAPIResponse(BaseModel):
    status: str = Field("success", description="Response status (success/error)")
    correlation_id: str = Field(..., description="Unique correlation ID tracing this request")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="UTC timestamp of the response")


class StandardResponse(BaseAPIResponse, Generic[T]):
    data: T = Field(..., description="Core payload returning data matching endpoint types")


class PaginatedResponse(BaseAPIResponse, Generic[T]):
    data: list[T] = Field(..., description="List payload of records for current page")
    pagination: PaginationMetadata = Field(..., description="Pagination metadata properties")


class ErrorDetails(BaseModel):
    code: str = Field("INTERNAL_SERVER_ERROR", description="Domain error code string")
    message: str = Field(..., description="User-facing error description")
    fields: Any | None = Field(None, description="Detailed field-level validation errors")


class ErrorResponse(BaseAPIResponse):
    status: str = Field("error")
    error: ErrorDetails

"""Common response schemas for health checks and pagination."""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(examples=["healthy"])
    database: str = Field(examples=["connected"])
    environment: str = Field(examples=["development"])
    version: str = Field(examples=["1.0.0"])


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response container."""

    model_config = ConfigDict(from_attributes=True)

    items: list[T]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)

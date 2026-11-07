"""Strict Pydantic schemas for Product catalog lifecycle."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductCreate(BaseModel):
    """Schema for creating a new catalog product."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    sku: str = Field(min_length=2, max_length=64, pattern=r"^[A-Za-z0-9\-_]+$")
    name: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    price: Decimal = Field(ge=Decimal("0.00"), max_digits=12, decimal_places=2)
    stock_quantity: int = Field(default=0, ge=0)
    min_stock: int = Field(default=5, ge=0)

    @field_validator("sku", mode="after")
    @classmethod
    def normalize_sku(cls, value: str) -> str:
        """Normalize SKU to uppercase."""
        return value.upper()


class ProductUpdate(BaseModel):
    """Schema for updating product metadata or price (stock changes use /inventory/movements)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    price: Decimal | None = Field(default=None, ge=Decimal("0.00"), max_digits=12, decimal_places=2)
    min_stock: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class ProductResponse(BaseModel):
    """Schema representing a Product returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sku: str
    name: str
    description: str | None
    price: Decimal
    stock_quantity: int
    min_stock: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

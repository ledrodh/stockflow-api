"""Pydantic schemas for Orders and OrderItems."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from stockflow.models.order import OrderStatus


class OrderItemCreate(BaseModel):
    """Line item input for creating an order."""

    model_config = ConfigDict(extra="forbid")

    product_id: UUID
    quantity: int = Field(gt=0, le=10000)


class OrderCreate(BaseModel):
    """Payload for placing an atomic order."""

    model_config = ConfigDict(extra="forbid")

    items: list[OrderItemCreate] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_unique_products(self) -> "OrderCreate":
        """Ensure each product_id appears at most once in the order items list."""
        seen: set[UUID] = set()
        for item in self.items:
            if item.product_id in seen:
                raise ValueError(
                    f"Duplicate product_id '{item.product_id}' in order items. "
                    "Combine quantities into a single line item."
                )
            seen.add(item.product_id)
        return self


class OrderItemResponse(BaseModel):
    """Response schema for an order line item with purchase-time snapshots."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    product_name_snapshot: str
    unit_price: Decimal
    quantity: int
    subtotal: Decimal


class OrderResponse(BaseModel):
    """Response schema for a processed Order."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    status: OrderStatus
    total_amount: Decimal
    items: list[OrderItemResponse]
    created_at: datetime
    updated_at: datetime

"""Pydantic schemas for administrative inventory movements."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from stockflow.models.inventory import MovementType


class InventoryMovementCreate(BaseModel):
    """Payload for registering an inventory movement (restock, return, or adjustment)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    product_id: UUID
    type: MovementType
    quantity: int = Field(gt=0, le=1_000_000)
    is_deduction: bool = Field(
        default=False,
        description="When type is ADJUSTMENT, if True, deducts quantity from stock.",
    )
    reference_id: str | None = Field(default=None, max_length=128)
    reason: str = Field(min_length=3, max_length=500)


class InventoryMovementResponse(BaseModel):
    """Immutable inventory movement ledger entry response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    type: MovementType
    quantity: int
    previous_stock: int
    new_stock: int
    reference_id: str | None
    reason: str
    created_by: UUID | None
    created_at: datetime

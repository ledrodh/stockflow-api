"""Pydantic schemas for administrative inventory movements."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from stockflow.models.inventory import AdjustmentDirection, MovementType


class InventoryMovementCreate(BaseModel):
    """Payload for registering an inventory movement (restock, return, or adjustment)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    product_id: UUID
    type: MovementType
    quantity: int = Field(gt=0, le=1_000_000)
    adjustment_direction: AdjustmentDirection | None = Field(
        default=None,
        description="Direction when type is ADJUSTMENT ('INCREASE' or 'DECREASE').",
    )
    is_deduction: bool | None = Field(
        default=None,
        description="Legacy flag: if provided on ADJUSTMENT, maps to adjustment_direction.",
    )
    reference_id: str | None = Field(default=None, max_length=128)
    reason: str = Field(min_length=3, max_length=500)

    @model_validator(mode="after")
    def validate_movement_rules(self) -> "InventoryMovementCreate":
        """Enforce domain rules for adjustments, returns, and directions."""
        if self.type == MovementType.ADJUSTMENT:
            if self.adjustment_direction is None:
                if self.is_deduction is True:
                    self.adjustment_direction = AdjustmentDirection.DECREASE
                elif self.is_deduction is False:
                    self.adjustment_direction = AdjustmentDirection.INCREASE
                else:
                    raise ValueError(
                        "adjustment_direction ('INCREASE' or 'DECREASE') "
                        "is required when type is ADJUSTMENT."
                    )
        elif self.adjustment_direction is not None:
            raise ValueError("adjustment_direction is only allowed when type is ADJUSTMENT.")

        if self.type == MovementType.RETURN and (
            not self.reference_id or not self.reference_id.strip()
        ):
            raise ValueError(
                "reference_id is strictly required for RETURN movements to ensure auditability."
            )

        return self


class InventoryMovementResponse(BaseModel):
    """Immutable inventory movement ledger entry response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    movement_sequence: int
    type: MovementType
    adjustment_direction: AdjustmentDirection | None = None
    quantity: int
    previous_stock: int
    new_stock: int
    reference_id: str | None = None
    reason: str
    created_by: UUID | None = None
    created_at: datetime

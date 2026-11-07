"""Immutable InventoryMovement ledger model for full stock traceability."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, event, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, Mapper, mapped_column

from stockflow.db.base import Base, UUIDPrimaryKeyMixin


class MovementType(StrEnum):
    """Inventory movement classifications."""

    IN = "IN"
    OUT = "OUT"
    ADJUSTMENT = "ADJUSTMENT"
    RETURN = "RETURN"


class InventoryMovement(UUIDPrimaryKeyMixin, Base):
    """Append-only immutable audit log recording every change in product stock."""

    __tablename__ = "inventory_movements"
    __table_args__ = (
        CheckConstraint(
            "type IN ('IN', 'OUT', 'ADJUSTMENT', 'RETURN')",
            name="valid_movement_type",
        ),
        CheckConstraint("quantity > 0", name="movement_quantity_positive"),
        CheckConstraint("previous_stock >= 0", name="previous_stock_non_negative"),
        CheckConstraint("new_stock >= 0", name="new_stock_non_negative"),
    )

    product_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    type: Mapped[str] = mapped_column(
        String(32),
        index=True,
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    previous_stock: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    new_stock: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    reference_id: Mapped[str | None] = mapped_column(
        String(128),
        index=True,
        nullable=True,
    )
    reason: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    created_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )


@event.listens_for(InventoryMovement, "before_update")
def _prevent_movement_update(
    _mapper: Mapper[Any], _connection: Any, _target: InventoryMovement
) -> None:
    raise ValueError("InventoryMovement records are immutable and cannot be updated.")


@event.listens_for(InventoryMovement, "before_delete")
def _prevent_movement_delete(
    _mapper: Mapper[Any], _connection: Any, _target: InventoryMovement
) -> None:
    raise ValueError("InventoryMovement records are immutable and cannot be deleted.")

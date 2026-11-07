"""Order and OrderItem models preserving purchase-time snapshots."""

from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from stockflow.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class OrderStatus(StrEnum):
    """Order lifecycle status."""

    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class Order(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Customer purchase order processed atomically."""

    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'CONFIRMED', 'CANCELLED')",
            name="valid_order_status",
        ),
        CheckConstraint("total_amount >= 0", name="total_amount_non_negative"),
    )

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default=OrderStatus.CONFIRMED.value,
        server_default=OrderStatus.CONFIRMED.value,
        nullable=False,
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class OrderItem(UUIDPrimaryKeyMixin, Base):
    """Line item within an Order capturing immutable product name and unit price snapshots."""

    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("unit_price >= 0", name="unit_price_non_negative"),
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("subtotal >= 0", name="subtotal_non_negative"),
    )

    order_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    product_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    product_name_snapshot: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    order: Mapped["Order"] = relationship("Order", back_populates="items")

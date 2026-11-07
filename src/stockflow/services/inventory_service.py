"""Administrative inventory movement service with row-level locking and immutable audit logs."""

from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from stockflow.core.config import settings
from stockflow.core.exceptions import InsufficientStockError, NotFoundError
from stockflow.models.inventory import InventoryMovement, MovementType
from stockflow.models.product import Product
from stockflow.schemas.common import PaginatedResponse
from stockflow.schemas.inventory import InventoryMovementCreate, InventoryMovementResponse


async def register_inventory_movement(
    session: AsyncSession,
    payload: InventoryMovementCreate,
    user_id: UUID,
) -> InventoryMovement:
    """Atomically lock the product row, update stock_quantity, and append an InventoryMovement."""
    async with session.begin_nested() if session.in_transaction() else session.begin():
        await session.execute(text(f"SET LOCAL lock_timeout = '{settings.DB_LOCK_TIMEOUT_MS}ms'"))

        stmt = select(Product).where(Product.id == payload.product_id).with_for_update()
        product = (await session.execute(stmt)).scalar_one_or_none()
        if product is None:
            raise NotFoundError(
                f"Product '{payload.product_id}' not found.",
                details={"product_id": str(payload.product_id)},
            )

        previous_stock = product.stock_quantity
        is_outbound = payload.type == MovementType.OUT or (
            payload.type == MovementType.ADJUSTMENT and payload.is_deduction
        )

        if is_outbound:
            if previous_stock < payload.quantity:
                raise InsufficientStockError(
                    f"Insufficient stock for product '{product.sku}'. "
                    f"Available: {previous_stock}, requested deduction: {payload.quantity}.",
                    details={
                        "product_id": str(product.id),
                        "sku": product.sku,
                        "available_stock": previous_stock,
                        "requested_quantity": payload.quantity,
                    },
                )
            new_stock = previous_stock - payload.quantity
        else:
            new_stock = previous_stock + payload.quantity

        product.stock_quantity = new_stock

        movement = InventoryMovement(
            product_id=product.id,
            type=payload.type.value,
            quantity=payload.quantity,
            previous_stock=previous_stock,
            new_stock=new_stock,
            reference_id=payload.reference_id,
            reason=payload.reason,
            created_by=user_id,
        )
        session.add(movement)
        await session.flush()

    if session.in_transaction():
        await session.commit()

    await session.refresh(movement)
    return movement


async def list_inventory_movements(
    session: AsyncSession,
    *,
    limit: int = 20,
    offset: int = 0,
    product_id: UUID | None = None,
    movement_type: MovementType | None = None,
) -> PaginatedResponse[InventoryMovementResponse]:
    """List immutable inventory movements with optional filtering."""
    base_stmt = select(InventoryMovement)
    if product_id is not None:
        base_stmt = base_stmt.where(InventoryMovement.product_id == product_id)
    if movement_type is not None:
        base_stmt = base_stmt.where(InventoryMovement.type == movement_type.value)

    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = (await session.execute(count_stmt)).scalar_one()

    items_stmt = (
        base_stmt.order_by(InventoryMovement.created_at.desc(), InventoryMovement.id.asc())
        .limit(limit)
        .offset(offset)
    )
    movements = (await session.execute(items_stmt)).scalars().all()

    return PaginatedResponse[InventoryMovementResponse](
        items=[InventoryMovementResponse.model_validate(m) for m in movements],
        total=total,
        limit=limit,
        offset=offset,
    )

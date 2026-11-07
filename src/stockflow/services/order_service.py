"""Atomic Order and Inventory engine with PostgreSQL idempotency and SELECT FOR UPDATE locking."""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from stockflow.core.config import settings
from stockflow.core.exceptions import (
    ConflictError,
    IdempotencyConflictError,
    InsufficientStockError,
    NotFoundError,
)
from stockflow.models.idempotency import IdempotencyKey, IdempotencyStatus
from stockflow.models.inventory import InventoryMovement, MovementType
from stockflow.models.order import Order, OrderItem, OrderStatus
from stockflow.models.product import Product
from stockflow.schemas.common import PaginatedResponse
from stockflow.schemas.order import OrderCreate, OrderItemResponse, OrderResponse


def compute_order_request_hash(payload: OrderCreate) -> str:
    """Compute a deterministic SHA-256 hash of the order request payload."""
    canonical_items = sorted(
        [{"product_id": str(item.product_id), "quantity": item.quantity} for item in payload.items],
        key=lambda x: str(x["product_id"]),
    )
    canonical_json = json.dumps({"items": canonical_items}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


async def _evaluate_existing_idempotency(
    session: AsyncSession,
    user_id: UUID,
    idempotency_key: str,
    request_hash: str,
) -> OrderResponse | None:
    """Check if an idempotency record already exists and validate its payload hash."""
    stmt = select(IdempotencyKey).where(
        IdempotencyKey.user_id == user_id,
        IdempotencyKey.key == idempotency_key,
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing is None:
        return None

    if existing.request_hash != request_hash:
        raise IdempotencyConflictError(
            "Idempotency-Key was already used with a different request payload.",
            details={"idempotency_key": idempotency_key},
        )

    if existing.status == IdempotencyStatus.COMPLETED.value and existing.response_body is not None:
        return OrderResponse.model_validate(existing.response_body)

    raise IdempotencyConflictError(
        "A request with this Idempotency-Key is currently being processed.",
        details={"idempotency_key": idempotency_key},
    )


async def create_order_atomic(
    session: AsyncSession,
    user_id: UUID,
    payload: OrderCreate,
    idempotency_key: str,
) -> OrderResponse:
    """Execute an atomic purchase order with idempotency, row locking, and audit trail.

    Workflow inside the atomic transaction:
    1. Insert IdempotencyKey with UNIQUE(user_id, key).
    2. Lock target Product rows ordered by Product.id ASC using SELECT ... FOR UPDATE.
    3. Verify active status and stock_quantity for ALL items; rollback automatically on failure.
    4. Deduct stock_quantity and create Order, OrderItems (snapshots), and InventoryMovements.
    5. Store the serialized OrderResponse in IdempotencyKey.response_body and commit.
    """
    clean_key = idempotency_key.strip()
    request_hash = compute_order_request_hash(payload)

    # Fast-path check before starting the write transaction if already in a read state
    if session.in_transaction():
        await session.rollback()

    try:
        async with session.begin():
            await session.execute(
                text(f"SET LOCAL lock_timeout = '{settings.DB_LOCK_TIMEOUT_MS}ms'")
            )

            # Check if key was already completed previously
            cached_response = await _evaluate_existing_idempotency(
                session, user_id, clean_key, request_hash
            )
            if cached_response is not None:
                return cached_response

            now = datetime.now(UTC)
            idem_record = IdempotencyKey(
                user_id=user_id,
                key=clean_key,
                request_hash=request_hash,
                status=IdempotencyStatus.PROCESSING.value,
                created_at=now,
                expires_at=now + timedelta(hours=settings.IDEMPOTENCY_TTL_HOURS),
            )
            session.add(idem_record)
            await session.flush()

            # Sort product IDs deterministically and lock rows with SELECT FOR UPDATE
            product_ids = [item.product_id for item in payload.items]
            products_stmt = (
                select(Product)
                .where(Product.id.in_(product_ids))
                .order_by(Product.id.asc())
                .with_for_update()
            )
            locked_products = (await session.execute(products_stmt)).scalars().all()
            products_by_id: dict[UUID, Product] = {prod.id: prod for prod in locked_products}

            # Verify all requested products exist and are active
            for item in payload.items:
                product = products_by_id.get(item.product_id)
                if product is None:
                    raise NotFoundError(
                        f"Product '{item.product_id}' not found.",
                        details={"product_id": str(item.product_id)},
                    )
                if not product.is_active:
                    raise ConflictError(
                        f"Product '{product.sku}' is inactive and cannot be purchased.",
                        details={"product_id": str(product.id), "sku": product.sku},
                    )

            # Verify stock sufficiency for ALL items before mutating anything
            for item in payload.items:
                product = products_by_id[item.product_id]
                if product.stock_quantity < item.quantity:
                    raise InsufficientStockError(
                        f"Insufficient stock for product '{product.sku}'. "
                        f"Available: {product.stock_quantity}, requested: {item.quantity}.",
                        details={
                            "product_id": str(product.id),
                            "sku": product.sku,
                            "available_stock": product.stock_quantity,
                            "requested_quantity": item.quantity,
                        },
                    )

            # Create Order, OrderItems (snapshots), and InventoryMovements
            order_id = uuid4()
            order_total = Decimal("0.00")
            order_items: list[OrderItem] = []
            response_items: list[OrderItemResponse] = []

            for item in payload.items:
                product = products_by_id[item.product_id]
                previous_stock = product.stock_quantity
                new_stock = previous_stock - item.quantity
                product.stock_quantity = new_stock

                unit_price = product.price
                subtotal = (unit_price * Decimal(item.quantity)).quantize(Decimal("0.01"))
                order_total += subtotal

                order_item_id = uuid4()
                order_item = OrderItem(
                    id=order_item_id,
                    order_id=order_id,
                    product_id=product.id,
                    product_name_snapshot=product.name,
                    unit_price=unit_price,
                    quantity=item.quantity,
                    subtotal=subtotal,
                )
                order_items.append(order_item)

                movement = InventoryMovement(
                    product_id=product.id,
                    type=MovementType.OUT.value,
                    quantity=item.quantity,
                    previous_stock=previous_stock,
                    new_stock=new_stock,
                    reference_id=str(order_id),
                    reason=f"Purchase order {order_id}",
                    created_by=user_id,
                )
                session.add(movement)

                response_items.append(
                    OrderItemResponse(
                        id=order_item_id,
                        product_id=product.id,
                        product_name_snapshot=product.name,
                        unit_price=unit_price,
                        quantity=item.quantity,
                        subtotal=subtotal,
                    )
                )

            order = Order(
                id=order_id,
                user_id=user_id,
                status=OrderStatus.CONFIRMED.value,
                total_amount=order_total,
                created_at=now,
                updated_at=now,
                items=order_items,
            )
            session.add(order)
            await session.flush()

            order_response = OrderResponse(
                id=order.id,
                user_id=order.user_id,
                status=OrderStatus.CONFIRMED,
                total_amount=order.total_amount,
                items=response_items,
                created_at=order.created_at,
                updated_at=order.updated_at,
            )

            idem_record.status = IdempotencyStatus.COMPLETED.value
            idem_record.response_code = 201
            idem_record.response_body = order_response.model_dump(mode="json")

            return order_response

    except IntegrityError as exc:
        # Handle race condition when two identical Idempotency-Keys arrive simultaneously
        if session.in_transaction():
            await session.rollback()
        cached_after_race = await _evaluate_existing_idempotency(
            session, user_id, clean_key, request_hash
        )
        if cached_after_race is not None:
            return cached_after_race
        raise IdempotencyConflictError(
            "Concurrent request with the same Idempotency-Key detected.",
            details={"idempotency_key": clean_key},
        ) from exc


async def get_order_by_id(
    session: AsyncSession,
    order_id: UUID,
    user_id: UUID,
    *,
    is_admin: bool = False,
) -> Order:
    """Fetch an order by ID, enforcing ownership unless user is admin."""
    stmt = select(Order).where(Order.id == order_id)
    if not is_admin:
        stmt = stmt.where(Order.user_id == user_id)

    order = (await session.execute(stmt)).scalar_one_or_none()
    if order is None:
        raise NotFoundError(
            f"Order '{order_id}' not found.",
            details={"order_id": str(order_id)},
        )
    return order


async def list_orders(
    session: AsyncSession,
    user_id: UUID,
    *,
    is_admin: bool = False,
    limit: int = 20,
    offset: int = 0,
) -> PaginatedResponse[OrderResponse]:
    """List orders (all orders for admins, own orders for customers)."""
    base_stmt = select(Order)
    if not is_admin:
        base_stmt = base_stmt.where(Order.user_id == user_id)

    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = (await session.execute(count_stmt)).scalar_one()

    items_stmt = (
        base_stmt.order_by(Order.created_at.desc(), Order.id.asc()).limit(limit).offset(offset)
    )
    orders = (await session.execute(items_stmt)).scalars().all()

    return PaginatedResponse[OrderResponse](
        items=[OrderResponse.model_validate(o) for o in orders],
        total=total,
        limit=limit,
        offset=offset,
    )

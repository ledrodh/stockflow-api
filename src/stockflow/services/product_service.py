"""Product catalog service implementing CRUD, search, pagination, and soft delete."""

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from stockflow.core.exceptions import ConflictError, NotFoundError
from stockflow.models.inventory import InventoryMovement, MovementType
from stockflow.models.product import Product
from stockflow.schemas.common import PaginatedResponse
from stockflow.schemas.product import ProductCreate, ProductResponse, ProductUpdate


async def create_product(
    session: AsyncSession,
    payload: ProductCreate,
    created_by: UUID | None = None,
) -> Product:
    """Create a product and record an initial inventory movement if initial stock > 0."""
    sku_check = select(Product).where(Product.sku == payload.sku)
    existing = (await session.execute(sku_check)).scalar_one_or_none()
    if existing is not None:
        raise ConflictError(
            f"Product with SKU '{payload.sku}' already exists.",
            details={"sku": payload.sku},
        )

    product = Product(
        sku=payload.sku,
        name=payload.name,
        description=payload.description,
        price=payload.price,
        stock_quantity=payload.stock_quantity,
        min_stock=payload.min_stock,
        is_active=True,
    )
    session.add(product)

    try:
        await session.flush()
        if payload.stock_quantity > 0:
            initial_movement = InventoryMovement(
                product_id=product.id,
                type=MovementType.IN.value,
                quantity=payload.stock_quantity,
                previous_stock=0,
                new_stock=payload.stock_quantity,
                reference_id=f"INIT-{product.sku}",
                reason="Initial product catalog stock entry",
                created_by=created_by,
            )
            session.add(initial_movement)
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError(
            f"Product with SKU '{payload.sku}' already exists.",
            details={"sku": payload.sku},
        ) from exc

    await session.refresh(product)
    return product


async def get_product_by_id(
    session: AsyncSession,
    product_id: UUID,
    *,
    include_inactive: bool = False,
) -> Product:
    """Fetch a single product by ID, respecting soft-deletion filter."""
    stmt = select(Product).where(Product.id == product_id)
    if not include_inactive:
        stmt = stmt.where(Product.is_active.is_(True))

    product = (await session.execute(stmt)).scalar_one_or_none()
    if product is None:
        raise NotFoundError(
            f"Product '{product_id}' not found.",
            details={"product_id": str(product_id)},
        )
    return product


async def list_products(
    session: AsyncSession,
    *,
    limit: int = 20,
    offset: int = 0,
    search: str | None = None,
    include_inactive: bool = False,
) -> PaginatedResponse[ProductResponse]:
    """List products with limit/offset pagination and case-insensitive search on name and SKU."""
    base_stmt = select(Product)
    if not include_inactive:
        base_stmt = base_stmt.where(Product.is_active.is_(True))

    if search and search.strip():
        pattern = f"%{search.strip()}%"
        base_stmt = base_stmt.where(
            or_(
                Product.name.ilike(pattern),
                Product.sku.ilike(pattern),
            )
        )

    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total = (await session.execute(count_stmt)).scalar_one()

    items_stmt = (
        base_stmt.order_by(Product.created_at.desc(), Product.id.asc()).limit(limit).offset(offset)
    )
    products = (await session.execute(items_stmt)).scalars().all()

    return PaginatedResponse[ProductResponse](
        items=[ProductResponse.model_validate(prod) for prod in products],
        total=total,
        limit=limit,
        offset=offset,
    )


async def update_product(
    session: AsyncSession,
    product_id: UUID,
    payload: ProductUpdate,
) -> Product:
    """Update product fields (excluding stock_quantity, which requires an InventoryMovement)."""
    product = await get_product_by_id(session, product_id, include_inactive=True)

    update_data = payload.model_dump(exclude_unset=True)
    for field_name, value in update_data.items():
        setattr(product, field_name, value)

    await session.commit()
    await session.refresh(product)
    return product


async def soft_delete_product(
    session: AsyncSession,
    product_id: UUID,
) -> Product:
    """Logically delete a product by setting is_active=False, preserving historical orders."""
    product = await get_product_by_id(session, product_id, include_inactive=True)
    product.is_active = False
    await session.commit()
    await session.refresh(product)
    return product

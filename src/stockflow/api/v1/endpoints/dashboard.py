"""Dashboard metrics endpoint providing aggregated KPIs and recent audit logs."""

from decimal import Decimal

from fastapi import APIRouter
from sqlalchemy import func, select

from stockflow.api.dependencies import DBSessionDep, OptionalCurrentUserDep
from stockflow.models.inventory import InventoryMovement
from stockflow.models.order import Order, OrderStatus
from stockflow.models.product import Product
from stockflow.schemas.dashboard import DashboardSummaryResponse
from stockflow.schemas.inventory import InventoryMovementResponse
from stockflow.schemas.order import OrderResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    summary="Get aggregated inventory and sales metrics for dashboard overview",
)
async def get_dashboard_summary(
    session: DBSessionDep,
    _current_user: OptionalCurrentUserDep,
) -> DashboardSummaryResponse:
    """Calculate inventory KPIs, order counts, revenue, and fetch recent activity."""
    # 1. Total products (active)
    total_products = (
        await session.execute(
            select(func.count()).select_from(Product).where(Product.is_active.is_(True))
        )
    ).scalar_one()

    # 2. Total stock units
    total_stock_res = (
        await session.execute(
            select(func.coalesce(func.sum(Product.stock_quantity), 0)).where(
                Product.is_active.is_(True)
            )
        )
    ).scalar_one()
    total_stock_items = int(total_stock_res)

    # 3. Low stock products (< 5 units)
    low_stock_products = (
        await session.execute(
            select(func.count())
            .select_from(Product)
            .where(Product.is_active.is_(True), Product.stock_quantity < 5)
        )
    ).scalar_one()

    # 4. Total confirmed orders & revenue
    orders_res = (
        await session.execute(
            select(
                func.count(Order.id),
                func.coalesce(func.sum(Order.total_amount), Decimal("0.00")),
            ).where(Order.status == OrderStatus.CONFIRMED.value)
        )
    ).one()
    total_orders = int(orders_res[0])
    total_revenue = Decimal(orders_res[1])

    # 5. Recent 5 orders
    recent_orders_stmt = select(Order).order_by(Order.created_at.desc()).limit(5)
    orders = (await session.execute(recent_orders_stmt)).scalars().all()

    # 6. Recent 5 inventory movements
    recent_movements_stmt = (
        select(InventoryMovement).order_by(InventoryMovement.created_at.desc()).limit(5)
    )
    movements = (await session.execute(recent_movements_stmt)).scalars().all()

    return DashboardSummaryResponse(
        total_products=total_products,
        total_stock_items=total_stock_items,
        low_stock_products=low_stock_products,
        total_orders=total_orders,
        total_revenue=total_revenue,
        recent_orders=[OrderResponse.model_validate(o) for o in orders],
        recent_movements=[InventoryMovementResponse.model_validate(m) for m in movements],
    )

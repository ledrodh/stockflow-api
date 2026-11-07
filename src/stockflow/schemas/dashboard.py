"""Dashboard analytics and statistics schemas."""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from stockflow.schemas.inventory import InventoryMovementResponse
from stockflow.schemas.order import OrderResponse


class DashboardSummaryResponse(BaseModel):
    """Aggregated metrics and recent activity for the management dashboard."""

    model_config = ConfigDict(from_attributes=True)

    total_products: int = Field(ge=0)
    total_stock_items: int = Field(ge=0)
    low_stock_products: int = Field(ge=0)
    total_orders: int = Field(ge=0)
    total_revenue: Decimal = Field(ge=Decimal("0.00"))
    recent_orders: list[OrderResponse]
    recent_movements: list[InventoryMovementResponse]

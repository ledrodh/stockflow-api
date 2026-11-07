"""Pydantic schemas for the Stock Reconciliation Engine."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProductDiscrepancy(BaseModel):
    """Detailed discrepancy diagnostic for an individual product."""

    model_config = ConfigDict(extra="forbid")

    product_id: UUID
    sku: str
    product_name: str
    current_stock_quantity: int
    calculated_ledger_stock: int
    discrepancy_delta: int
    sequence_errors: list[str] = Field(default_factory=list)
    continuity_errors: list[str] = Field(default_factory=list)
    arithmetic_errors: list[str] = Field(default_factory=list)
    is_consistent: bool = True


class StockReconciliationReport(BaseModel):
    """System-wide ledger vs. snapshot stock reconciliation report."""

    model_config = ConfigDict(extra="forbid")

    generated_at: datetime
    snapshot_isolation_level: str = "REPEATABLE READ, READ ONLY"
    total_products_checked: int
    consistent_products_count: int
    discrepant_products_count: int
    is_consistent: bool
    discrepancies: list[ProductDiscrepancy] = Field(default_factory=list)

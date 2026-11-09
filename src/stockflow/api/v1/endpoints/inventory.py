"""Administrative inventory movement endpoints (restock, return, adjustment, audit log)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from stockflow.api.dependencies import AdminUserDep, DBSessionDep
from stockflow.models.inventory import MovementType
from stockflow.schemas.common import PaginatedResponse
from stockflow.schemas.inventory import InventoryMovementCreate, InventoryMovementResponse
from stockflow.schemas.reconciliation import StockReconciliationReport
from stockflow.services.inventory_service import (
    list_inventory_movements,
    register_inventory_movement,
)
from stockflow.services.reconciliation_service import run_inventory_reconciliation

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.post(
    "/movements",
    response_model=InventoryMovementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register an administrative inventory movement (Admin only)",
)
async def create_inventory_movement_endpoint(
    payload: InventoryMovementCreate,
    session: DBSessionDep,
    admin_user: AdminUserDep,
) -> InventoryMovementResponse:
    """Atomically adjust product stock and record an immutable InventoryMovement entry."""
    movement = await register_inventory_movement(
        session=session,
        payload=payload,
        user_id=admin_user.id,
    )
    return InventoryMovementResponse.model_validate(movement)


@router.get(
    "/movements",
    response_model=PaginatedResponse[InventoryMovementResponse],
    summary="List immutable inventory movement ledger entries (Admin only)",
)
async def list_inventory_movements_endpoint(
    session: DBSessionDep,
    _admin_user: AdminUserDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=2_147_483_647)] = 0,
    product_id: Annotated[UUID | None, Query()] = None,
    movement_type: Annotated[MovementType | None, Query(alias="type")] = None,
) -> PaginatedResponse[InventoryMovementResponse]:
    """Retrieve the immutable audit log of inventory movements."""
    return await list_inventory_movements(
        session=session,
        limit=limit,
        offset=offset,
        product_id=product_id,
        movement_type=movement_type,
    )


@router.get(
    "/reconcile",
    response_model=StockReconciliationReport,
    summary="Run snapshot-consistent inventory ledger reconciliation (Admin only)",
)
async def reconcile_inventory_endpoint(
    session: DBSessionDep,
    _admin_user: AdminUserDep,
) -> StockReconciliationReport:
    """Execute 3-level ledger verification under REPEATABLE READ snapshot isolation."""
    return await run_inventory_reconciliation(session=session)

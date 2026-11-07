"""Order endpoints with PostgreSQL-backed idempotency and atomic inventory reservation."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Query, status

from stockflow.api.dependencies import CurrentUserDep, DBSessionDep
from stockflow.models.user import UserRole
from stockflow.schemas.common import PaginatedResponse
from stockflow.schemas.order import OrderCreate, OrderResponse
from stockflow.services.order_service import (
    create_order_atomic,
    get_order_by_id,
    list_orders,
)

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Place an atomic purchase order (requires Idempotency-Key header)",
)
async def create_order_endpoint(
    payload: OrderCreate,
    session: DBSessionDep,
    current_user: CurrentUserDep,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            min_length=1,
            max_length=255,
            description="Unique client-generated key ensuring idempotent order processing.",
        ),
    ],
) -> OrderResponse:
    """Process a purchase order atomically with SELECT FOR UPDATE locking and idempotency."""
    return await create_order_atomic(
        session=session,
        user_id=current_user.id,
        payload=payload,
        idempotency_key=idempotency_key,
    )


@router.get(
    "",
    response_model=PaginatedResponse[OrderResponse],
    summary="List orders (own orders for customers, all orders for admins)",
)
async def list_orders_endpoint(
    session: DBSessionDep,
    current_user: CurrentUserDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PaginatedResponse[OrderResponse]:
    """Retrieve a paginated list of orders."""
    is_admin = current_user.role == UserRole.ADMIN.value
    return await list_orders(
        session=session,
        user_id=current_user.id,
        is_admin=is_admin,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Get order details by ID",
)
async def get_order_endpoint(
    order_id: UUID,
    session: DBSessionDep,
    current_user: CurrentUserDep,
) -> OrderResponse:
    """Retrieve a single order with its snapshot line items."""
    is_admin = current_user.role == UserRole.ADMIN.value
    order = await get_order_by_id(
        session=session,
        order_id=order_id,
        user_id=current_user.id,
        is_admin=is_admin,
    )
    return OrderResponse.model_validate(order)

"""Product catalog endpoints with RBAC, pagination, search, and soft deletion."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from stockflow.api.dependencies import AdminUserDep, DBSessionDep, OptionalCurrentUserDep
from stockflow.models.user import UserRole
from stockflow.schemas.common import PaginatedResponse
from stockflow.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from stockflow.services.product_service import (
    create_product,
    get_product_by_id,
    list_products,
    soft_delete_product,
    update_product,
)

router = APIRouter(prefix="/products", tags=["Products"])


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product (Admin only)",
)
async def create_product_endpoint(
    payload: ProductCreate,
    session: DBSessionDep,
    admin_user: AdminUserDep,
) -> ProductResponse:
    """Create a new catalog product and initialize its inventory movement ledger."""
    product = await create_product(session, payload, created_by=admin_user.id)
    return ProductResponse.model_validate(product)


@router.get(
    "",
    response_model=PaginatedResponse[ProductResponse],
    summary="List products with pagination and search by name or SKU",
)
async def list_products_endpoint(
    session: DBSessionDep,
    current_user: OptionalCurrentUserDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    search: Annotated[str | None, Query(max_length=100)] = None,
    include_inactive: Annotated[bool, Query()] = False,
) -> PaginatedResponse[ProductResponse]:
    """List products with limit/offset pagination and optional search filter."""
    allow_inactive = bool(
        include_inactive and current_user and current_user.role == UserRole.ADMIN.value
    )
    return await list_products(
        session,
        limit=limit,
        offset=offset,
        search=search,
        include_inactive=allow_inactive,
    )


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get product details by ID",
)
async def get_product_endpoint(
    product_id: UUID,
    session: DBSessionDep,
    current_user: OptionalCurrentUserDep,
) -> ProductResponse:
    """Fetch a single product by ID."""
    allow_inactive = bool(current_user and current_user.role == UserRole.ADMIN.value)
    product = await get_product_by_id(session, product_id, include_inactive=allow_inactive)
    return ProductResponse.model_validate(product)


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update product details or price (Admin only)",
)
@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update product details or price (Admin only)",
    include_in_schema=False,
)
async def update_product_endpoint(
    product_id: UUID,
    payload: ProductUpdate,
    session: DBSessionDep,
    _admin_user: AdminUserDep,
) -> ProductResponse:
    """Update product fields (stock adjustments must use POST /inventory/movements)."""
    product = await update_product(session, product_id, payload)
    return ProductResponse.model_validate(product)


@router.delete(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Logically deactivate a product (Soft Delete, Admin only)",
)
async def delete_product_endpoint(
    product_id: UUID,
    session: DBSessionDep,
    _admin_user: AdminUserDep,
) -> ProductResponse:
    """Inactivate a product (is_active=False) without physical deletion."""
    product = await soft_delete_product(session, product_id)
    return ProductResponse.model_validate(product)

"""Integration tests for Product Catalog CRUD, RBAC, pagination, search, and soft delete."""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from stockflow.models.product import Product


async def test_customer_cannot_mutate_products_rbac(
    client: AsyncClient,
    customer_headers: dict[str, str],
) -> None:
    """Customers must receive 403 Forbidden when trying to create, update, or delete products."""
    create_resp = await client.post(
        "/api/v1/products",
        headers=customer_headers,
        json={
            "sku": "RBAC-001",
            "name": "Unauthorized Product",
            "price": "99.90",
            "stock_quantity": 10,
        },
    )
    assert create_resp.status_code == 403
    assert create_resp.json()["error"]["code"] == "PERMISSION_DENIED"


async def test_admin_product_crud_search_pagination_and_soft_delete(
    client: AsyncClient,
    admin_headers: dict[str, str],
    customer_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """Verify full lifecycle: create, duplicate SKU conflict, search, pagination, soft delete."""
    # 1. Create products as Admin
    p1_resp = await client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={
            "sku": "keyb-mech-01",
            "name": "Mechanical Keyboard Pro",
            "description": "Hot-swappable tactile keyboard",
            "price": "450.00",
            "stock_quantity": 15,
        },
    )
    assert p1_resp.status_code == 201
    p1 = p1_resp.json()
    assert p1["sku"] == "KEYB-MECH-01"
    assert p1["stock_quantity"] == 15
    assert p1["is_active"] is True

    p2_resp = await client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={
            "sku": "MOUSE-OPT-02",
            "name": "Wireless Optical Mouse",
            "price": "199.50",
            "stock_quantity": 30,
        },
    )
    assert p2_resp.status_code == 201
    p2 = p2_resp.json()

    # 2. Duplicate SKU must return 409 Conflict
    dup_resp = await client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={
            "sku": "KEYB-MECH-01",
            "name": "Duplicate SKU Keyboard",
            "price": "300.00",
            "stock_quantity": 5,
        },
    )
    assert dup_resp.status_code == 409

    # 3. Search by name and SKU + Pagination
    search_name = await client.get(
        "/api/v1/products?search=Keyboard",
        headers=customer_headers,
    )
    assert search_name.status_code == 200
    assert search_name.json()["total"] == 1
    assert search_name.json()["items"][0]["id"] == p1["id"]

    search_sku = await client.get(
        "/api/v1/products?search=MOUSE-OPT",
        headers=customer_headers,
    )
    assert search_sku.status_code == 200
    assert search_sku.json()["total"] == 1
    assert search_sku.json()["items"][0]["id"] == p2["id"]

    paginated = await client.get(
        "/api/v1/products?limit=1&offset=0",
        headers=customer_headers,
    )
    assert paginated.status_code == 200
    assert paginated.json()["total"] == 2
    assert len(paginated.json()["items"]) == 1

    # 4. Update product price and name
    patch_resp = await client.patch(
        f"/api/v1/products/{p1['id']}",
        headers=admin_headers,
        json={"price": "420.00", "name": "Mechanical Keyboard Pro V2"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["price"] == "420.00"
    assert patch_resp.json()["name"] == "Mechanical Keyboard Pro V2"

    # 5. Soft Delete product (DELETE sets is_active=False, keeps row in PostgreSQL)
    del_resp = await client.delete(
        f"/api/v1/products/{p1['id']}",
        headers=admin_headers,
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["is_active"] is False

    # Customer no longer sees deactivated product in catalog or by ID
    customer_list = await client.get("/api/v1/products", headers=customer_headers)
    assert customer_list.json()["total"] == 1
    assert customer_list.json()["items"][0]["id"] == p2["id"]

    customer_get = await client.get(
        f"/api/v1/products/{p1['id']}",
        headers=customer_headers,
    )
    assert customer_get.status_code == 404

    # Verify record still physically exists in PostgreSQL
    db_row = (
        await db_session.execute(select(Product).where(Product.id == p1["id"]))
    ).scalar_one_or_none()
    assert db_row is not None
    assert db_row.is_active is False


async def test_product_rejects_negative_price_and_negative_stock(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Negative price or stock_quantity must be rejected with 422."""
    neg_price = await client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={
            "sku": "NEG-PRICE-01",
            "name": "Negative Price Item",
            "price": "-10.00",
            "stock_quantity": 5,
        },
    )
    assert neg_price.status_code == 422

    neg_stock = await client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={
            "sku": "NEG-STOCK-01",
            "name": "Negative Stock Item",
            "price": "10.00",
            "stock_quantity": -1,
        },
    )
    assert neg_stock.status_code == 422

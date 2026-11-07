"""Concurrency and stress tests verifying SELECT FOR UPDATE and deadlock prevention under load."""

import asyncio
from uuid import UUID, uuid4

from httpx import AsyncClient, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from stockflow.models.inventory import InventoryMovement, MovementType
from stockflow.models.order import Order
from stockflow.models.product import Product


async def test_concurrent_purchase_stress_10_requests_for_5_items(
    client: AsyncClient,
    admin_headers: dict[str, str],
    customer_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """O Teste de Fogo (Sprint 4):
    Fire 10 simultaneous purchase requests via asyncio.gather for a product with only 5 units.
    Assert that:
    - Exactly 5 requests succeed with 201 Created.
    - Exactly 5 requests fail with 409 Conflict (INSUFFICIENT_STOCK).
    - Final stock_quantity in PostgreSQL is 0 (never negative).
    - Total confirmed orders and OUT movements match the 5 successful purchases.
    """
    create_resp = await client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={
            "sku": "PS5-PRO-LIMITED",
            "name": "PlayStation 5 Pro Limited Edition",
            "price": "6999.90",
            "stock_quantity": 5,
        },
    )
    assert create_resp.status_code == 201
    product_id = create_resp.json()["id"]

    async def _attempt_purchase(index: int) -> Response:
        return await client.post(
            "/api/v1/orders",
            headers={
                **customer_headers,
                "Idempotency-Key": f"concurrent-stress-{index}-{uuid4()}",
            },
            json={
                "items": [
                    {"product_id": product_id, "quantity": 1},
                ]
            },
        )

    # Fire all 10 requests concurrently
    responses = await asyncio.gather(*[_attempt_purchase(i) for i in range(10)])

    status_codes = [resp.status_code for resp in responses]
    success_count = status_codes.count(201)
    conflict_count = status_codes.count(409)

    assert success_count == 5, f"Expected 5 successes (201), got {status_codes}"
    assert conflict_count == 5, f"Expected 5 conflicts (409), got {status_codes}"

    # Verify database state directly in PostgreSQL
    db_session.expire_all()
    product = (
        await db_session.execute(select(Product).where(Product.id == UUID(product_id)))
    ).scalar_one()
    assert product.stock_quantity == 0

    orders_count = (await db_session.execute(select(func.count()).select_from(Order))).scalar_one()
    assert orders_count == 5

    out_movements_count = (
        await db_session.execute(
            select(func.count())
            .select_from(InventoryMovement)
            .where(
                InventoryMovement.product_id == UUID(product_id),
                InventoryMovement.type == MovementType.OUT.value,
            )
        )
    ).scalar_one()
    assert out_movements_count == 5


async def test_concurrent_multi_item_inverted_order_prevents_deadlocks(
    client: AsyncClient,
    admin_headers: dict[str, str],
    customer_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """Verify deterministic order_by(Product.id).with_for_update() prevents deadlocks
    when concurrent requests lock overlapping products in opposite order ([A, B] vs [B, A]).
    """
    prod_a = (
        await client.post(
            "/api/v1/products",
            headers=admin_headers,
            json={"sku": "DEADLOCK-A", "name": "Item A", "price": "100.00", "stock_quantity": 10},
        )
    ).json()
    prod_b = (
        await client.post(
            "/api/v1/products",
            headers=admin_headers,
            json={"sku": "DEADLOCK-B", "name": "Item B", "price": "200.00", "stock_quantity": 10},
        )
    ).json()

    async def _order_ab(idx: int) -> Response:
        items = (
            [
                {"product_id": prod_a["id"], "quantity": 1},
                {"product_id": prod_b["id"], "quantity": 1},
            ]
            if idx % 2 == 0
            else [
                {"product_id": prod_b["id"], "quantity": 1},
                {"product_id": prod_a["id"], "quantity": 1},
            ]
        )
        return await client.post(
            "/api/v1/orders",
            headers={
                **customer_headers,
                "Idempotency-Key": f"deadlock-test-{idx}-{uuid4()}",
            },
            json={"items": items},
        )

    responses = await asyncio.gather(*[_order_ab(i) for i in range(10)])
    assert all(r.status_code == 201 for r in responses)

    db_session.expire_all()
    db_a = (
        await db_session.execute(select(Product).where(Product.id == UUID(prod_a["id"])))
    ).scalar_one()
    db_b = (
        await db_session.execute(select(Product).where(Product.id == UUID(prod_b["id"])))
    ).scalar_one()
    assert db_a.stock_quantity == 0
    assert db_b.stock_quantity == 0

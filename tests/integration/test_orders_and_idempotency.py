"""Integration tests for atomic Order processing, PostgreSQL Idempotency, and Immutable Ledger."""

import asyncio
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession


async def test_atomic_order_snapshots_idempotency_and_traceability(
    client: AsyncClient,
    admin_headers: dict[str, str],
    customer_headers: dict[str, str],
) -> None:
    """Verify atomic purchase, idempotent replay, payload conflict (409), and snapshots."""
    # 1. Create product with initial stock = 10
    prod_resp = await client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={
            "sku": "GPU-RTX-5090",
            "name": "GeForce RTX 5090 32GB",
            "price": "12500.00",
            "stock_quantity": 10,
        },
    )
    assert prod_resp.status_code == 201
    product_id = prod_resp.json()["id"]

    # 2. Place an order with Idempotency-Key
    idem_key = f"order-key-{uuid4()}"
    order_payload = {
        "items": [
            {"product_id": product_id, "quantity": 2},
        ]
    }
    order_resp = await client.post(
        "/api/v1/orders",
        headers={**customer_headers, "Idempotency-Key": idem_key},
        json=order_payload,
    )
    assert order_resp.status_code == 201
    order_data = order_resp.json()
    assert order_data["status"] == "CONFIRMED"
    assert order_data["total_amount"] == "25000.00"
    assert len(order_data["items"]) == 1
    assert order_data["items"][0]["product_name_snapshot"] == "GeForce RTX 5090 32GB"
    assert order_data["items"][0]["unit_price"] == "12500.00"
    assert order_data["items"][0]["quantity"] == 2
    assert order_data["items"][0]["subtotal"] == "25000.00"

    # 3. Repeat exact same request with same Idempotency-Key -> returns same order
    replay_resp = await client.post(
        "/api/v1/orders",
        headers={**customer_headers, "Idempotency-Key": idem_key},
        json=order_payload,
    )
    assert replay_resp.status_code == 201
    assert replay_resp.json()["id"] == order_data["id"]

    # Check stock is 8 (not 6!)
    prod_after = await client.get(f"/api/v1/products/{product_id}", headers=customer_headers)
    assert prod_after.json()["stock_quantity"] == 8

    # 4. Reuse same Idempotency-Key with a DIFFERENT payload -> must return 409 Conflict
    conflict_resp = await client.post(
        "/api/v1/orders",
        headers={**customer_headers, "Idempotency-Key": idem_key},
        json={
            "items": [
                {"product_id": product_id, "quantity": 3},
            ]
        },
    )
    assert conflict_resp.status_code == 409
    assert conflict_resp.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"

    # 5. Update product name and price, then soft-delete it; verify Order snapshot is preserved!
    await client.patch(
        f"/api/v1/products/{product_id}",
        headers=admin_headers,
        json={"name": "GeForce RTX 5090 Ti", "price": "15999.00"},
    )
    await client.delete(f"/api/v1/products/{product_id}", headers=admin_headers)

    historical_order = await client.get(
        f"/api/v1/orders/{order_data['id']}",
        headers=customer_headers,
    )
    assert historical_order.status_code == 200
    assert historical_order.json()["items"][0]["product_name_snapshot"] == "GeForce RTX 5090 32GB"
    assert historical_order.json()["items"][0]["unit_price"] == "12500.00"


async def test_multi_item_order_rolls_back_completely_if_one_item_fails(
    client: AsyncClient,
    admin_headers: dict[str, str],
    customer_headers: dict[str, str],
) -> None:
    """If any item in a multi-item order lacks stock, the entire transaction must roll back."""
    p1 = (
        await client.post(
            "/api/v1/products",
            headers=admin_headers,
            json={"sku": "CPU-01", "name": "Ryzen 9", "price": "3500.00", "stock_quantity": 10},
        )
    ).json()
    p2 = (
        await client.post(
            "/api/v1/products",
            headers=admin_headers,
            json={
                "sku": "MB-01",
                "name": "Motherboard X870",
                "price": "2200.00",
                "stock_quantity": 1,
            },
        )
    ).json()

    # Attempt to buy 3 units of CPU (available: 10) and 2 units of Motherboard (available: 1)
    order_resp = await client.post(
        "/api/v1/orders",
        headers={**customer_headers, "Idempotency-Key": f"atomic-rollback-{uuid4()}"},
        json={
            "items": [
                {"product_id": p1["id"], "quantity": 3},
                {"product_id": p2["id"], "quantity": 2},
            ]
        },
    )
    assert order_resp.status_code == 409
    assert order_resp.json()["error"]["code"] == "INSUFFICIENT_STOCK"

    # Verify CPU stock was NOT decremented (remained 10)
    p1_check = await client.get(f"/api/v1/products/{p1['id']}", headers=customer_headers)
    assert p1_check.json()["stock_quantity"] == 10


async def test_admin_inventory_movements_and_immutability(
    client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """Verify POST /inventory/movements (IN, RETURN, ADJUSTMENT, OUT) and ledger immutability."""
    prod = (
        await client.post(
            "/api/v1/products",
            headers=admin_headers,
            json={
                "sku": "SSD-NVME-2TB",
                "name": "NVMe SSD 2TB",
                "price": "890.00",
                "stock_quantity": 5,
            },
        )
    ).json()
    product_id = prod["id"]

    # Register an IN movement (+10)
    in_resp = await client.post(
        "/api/v1/inventory/movements",
        headers=admin_headers,
        json={
            "product_id": product_id,
            "type": "IN",
            "quantity": 10,
            "reference_id": "PO-2026-001",
            "reason": "Supplier restock shipment",
        },
    )
    assert in_resp.status_code == 201
    mov_data = in_resp.json()
    assert mov_data["previous_stock"] == 5
    assert mov_data["new_stock"] == 15

    # Register an ADJUSTMENT deduction (-3)
    adj_resp = await client.post(
        "/api/v1/inventory/movements",
        headers=admin_headers,
        json={
            "product_id": product_id,
            "type": "ADJUSTMENT",
            "quantity": 3,
            "is_deduction": True,
            "reference_id": "AUDIT-2026-01",
            "reason": "Damaged packaging found during warehouse audit",
        },
    )
    assert adj_resp.status_code == 201
    assert adj_resp.json()["previous_stock"] == 15
    assert adj_resp.json()["new_stock"] == 12

    # List movements for this product (1 initial + 1 IN + 1 ADJUSTMENT = 3 movements)
    list_resp = await client.get(
        f"/api/v1/inventory/movements?product_id={product_id}",
        headers=admin_headers,
    )
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 3

    # Verify PostgreSQL trigger prevents direct SQL DELETE or UPDATE on inventory_movements
    with pytest.raises(DBAPIError, match="immutable"):
        await db_session.execute(
            text("DELETE FROM inventory_movements WHERE id = :id"),
            {"id": mov_data["id"]},
        )
    await db_session.rollback()


async def test_concurrent_same_idempotency_key_race_condition(
    client: AsyncClient,
    admin_headers: dict[str, str],
    customer_headers: dict[str, str],
) -> None:
    """Two concurrent requests with the identical idempotency key and payload yield one order."""
    prod = (
        await client.post(
            "/api/v1/products",
            headers=admin_headers,
            json={
                "sku": "KEYBOARD-RACE",
                "name": "Mechanical Keyboard",
                "price": "450.00",
                "stock_quantity": 10,
            },
        )
    ).json()
    product_id = prod["id"]

    same_key = f"race-idem-{uuid4()}"
    payload = {"items": [{"product_id": product_id, "quantity": 2}]}

    req1 = client.post(
        "/api/v1/orders",
        headers={**customer_headers, "Idempotency-Key": same_key},
        json=payload,
    )
    req2 = client.post(
        "/api/v1/orders",
        headers={**customer_headers, "Idempotency-Key": same_key},
        json=payload,
    )

    resp1, resp2 = await asyncio.gather(req1, req2)
    assert resp1.status_code == 201
    assert resp2.status_code == 201
    assert resp1.json()["id"] == resp2.json()["id"]

    # Stock should be 8, not 6
    check_prod = await client.get(f"/api/v1/products/{product_id}", headers=customer_headers)
    assert check_prod.json()["stock_quantity"] == 8


async def test_order_cancellation_and_inventory_restoration(
    client: AsyncClient,
    admin_headers: dict[str, str],
    customer_headers: dict[str, str],
) -> None:
    """Cancelling an order restores product stock, creates a RETURN movement, and is idempotent."""
    prod = (
        await client.post(
            "/api/v1/products",
            headers=admin_headers,
            json={
                "sku": "HEADSET-CANCEL",
                "name": "Wireless Headset",
                "price": "600.00",
                "stock_quantity": 10,
            },
        )
    ).json()
    product_id = prod["id"]

    order_resp = await client.post(
        "/api/v1/orders",
        headers={**customer_headers, "Idempotency-Key": f"cancel-test-{uuid4()}"},
        json={"items": [{"product_id": product_id, "quantity": 4}]},
    )
    assert order_resp.status_code == 201
    order_id = order_resp.json()["id"]

    # Stock before cancel is 6
    prod_mid = await client.get(f"/api/v1/products/{product_id}", headers=customer_headers)
    assert prod_mid.json()["stock_quantity"] == 6

    # Cancel the order
    cancel_resp = await client.post(
        f"/api/v1/orders/{order_id}/cancel",
        headers=customer_headers,
    )
    assert cancel_resp.status_code == 200
    cancel_data = cancel_resp.json()
    assert cancel_data["status"] == "CANCELLED"

    # Stock must be restored back to 10
    prod_restored = await client.get(f"/api/v1/products/{product_id}", headers=customer_headers)
    assert prod_restored.json()["stock_quantity"] == 10

    # Repeating the cancel request is idempotent: status remains CANCELLED without double-restocking
    repeat_cancel = await client.post(
        f"/api/v1/orders/{order_id}/cancel",
        headers=customer_headers,
    )
    assert repeat_cancel.status_code == 200
    assert repeat_cancel.json()["status"] == "CANCELLED"

    prod_still_10 = await client.get(f"/api/v1/products/{product_id}", headers=customer_headers)
    assert prod_still_10.json()["stock_quantity"] == 10

    # Verify inventory audit trail has a RETURN movement
    movements_resp = await client.get(
        f"/api/v1/inventory/movements?product_id={product_id}",
        headers=admin_headers,
    )
    assert movements_resp.status_code == 200
    movements = movements_resp.json()["items"]
    types = [m["type"] for m in movements]
    assert "RETURN" in types


async def test_idempotency_ttl_expiration_allows_new_order(
    client: AsyncClient,
    admin_headers: dict[str, str],
    customer_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """When an idempotency key expires past its TTL, the key can be reused for a new order."""
    prod = (
        await client.post(
            "/api/v1/products",
            headers=admin_headers,
            json={
                "sku": "MOUSE-TTL",
                "name": "Gaming Mouse",
                "price": "150.00",
                "stock_quantity": 20,
            },
        )
    ).json()
    product_id = prod["id"]

    idem_key = f"ttl-key-{uuid4()}"
    first_resp = await client.post(
        "/api/v1/orders",
        headers={**customer_headers, "Idempotency-Key": idem_key},
        json={"items": [{"product_id": product_id, "quantity": 1}]},
    )
    assert first_resp.status_code == 201
    first_order_id = first_resp.json()["id"]

    # Manually expire the key in the database
    expire_sql = (
        "UPDATE idempotency_keys SET expires_at = now() - INTERVAL '5 minutes' WHERE key = :key"
    )
    await db_session.execute(text(expire_sql), {"key": idem_key})
    await db_session.commit()

    # Expired key allows submitting a brand new order with different payload
    second_resp = await client.post(
        "/api/v1/orders",
        headers={**customer_headers, "Idempotency-Key": idem_key},
        json={"items": [{"product_id": product_id, "quantity": 2}]},
    )
    assert second_resp.status_code == 201
    second_order_id = second_resp.json()["id"]
    assert second_order_id != first_order_id

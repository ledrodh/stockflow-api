"""Integration test: Multi-product catalog, combined atomic cart purchase, and ledger audit."""

from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from stockflow.models.inventory import InventoryMovement, MovementType
from stockflow.models.product import Product


async def test_multi_product_lifecycle_and_cart_purchase(
    client: AsyncClient,
    admin_headers: dict[str, str],
    customer_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    # --------------------------------------------------------------------------
    # STAGE 1: Register multiple distinct products in the catalog (as Admin)
    # --------------------------------------------------------------------------
    initial_stocks: dict[str, int] = {
        "MONITOR-4K-32": 10,
        "KEYB-MECH-RGB": 25,
        "MOUSEPAD-XL": 50,
        "HEADSET-71-PRO": 15,
    }

    catalog_items = [
        {"sku": "MONITOR-4K-32", "name": 'Monitor 32" 4K UHD', "price": "3499.00", "stock": 10},
        {"sku": "KEYB-MECH-RGB", "name": "RGB Mechanical Keyboard", "price": "550.00", "stock": 25},
        {"sku": "MOUSEPAD-XL", "name": "Deskmat XL Mousepad", "price": "120.00", "stock": 50},
        {"sku": "HEADSET-71-PRO", "name": "Wireless 7.1 Headset", "price": "890.00", "stock": 15},
    ]

    created_products: dict[str, dict[str, Any]] = {}
    for item in catalog_items:
        response = await client.post(
            "/api/v1/products",
            headers=admin_headers,
            json={
                "sku": item["sku"],
                "name": item["name"],
                "price": item["price"],
                "stock_quantity": item["stock"],
            },
        )
        assert response.status_code == 201, f"Failed to register product {item['sku']}"
        created_products[str(item["sku"])] = response.json()

    # --------------------------------------------------------------------------
    # STAGE 2: Execute atomic purchase with mixed cart items (as Customer)
    # Purchasing: 2 Monitors, 3 Keyboards, 5 Mousepads, and 1 Headset
    # --------------------------------------------------------------------------
    cart_quantities = {
        "MONITOR-4K-32": 2,  # Subtotal: 2 * 3499.00 = 6998.00
        "KEYB-MECH-RGB": 3,  # Subtotal: 3 * 550.00  = 1650.00
        "MOUSEPAD-XL": 5,  # Subtotal: 5 * 120.00  = 600.00
        "HEADSET-71-PRO": 1,  # Subtotal: 1 * 890.00  = 890.00
    }
    # Expected total: 6998 + 1650 + 600 + 890 = 10138.00

    order_items_payload = [
        {"product_id": created_products[sku]["id"], "quantity": qty}
        for sku, qty in cart_quantities.items()
    ]

    idempotency_key = f"mixed-cart-{uuid4()}"
    order_response = await client.post(
        "/api/v1/orders",
        headers={**customer_headers, "Idempotency-Key": idempotency_key},
        json={"items": order_items_payload},
    )

    # --------------------------------------------------------------------------
    # STAGE 3: Verify the Order was processed successfully
    # --------------------------------------------------------------------------
    assert order_response.status_code == 201
    order_data = order_response.json()

    # Validate calculated total
    assert order_data["status"] == "CONFIRMED"
    assert Decimal(order_data["total_amount"]) == Decimal("10138.00")
    assert len(order_data["items"]) == 4

    # --------------------------------------------------------------------------
    # STAGE 4: Verify Stock Integrity and Historical Audit Ledger in PostgreSQL
    # --------------------------------------------------------------------------
    for sku, bought_qty in cart_quantities.items():
        prod_id = UUID(str(created_products[sku]["id"]))
        initial_stock = initial_stocks[sku]
        expected_stock = initial_stock - bought_qty

        # 4.1. Product stock decremented accurately
        db_session.expire_all()
        prod_in_db = (
            await db_session.execute(select(Product).where(Product.id == prod_id))
        ).scalar_one()
        assert prod_in_db.stock_quantity == expected_stock

        # 4.2. Immutable append-only audit record created in inventory_movements
        movements = (
            (
                await db_session.execute(
                    select(InventoryMovement).where(
                        InventoryMovement.product_id == prod_id,
                        InventoryMovement.type == MovementType.OUT.value,
                    )
                )
            )
            .scalars()
            .all()
        )

        assert len(movements) == 1
        mov = movements[0]
        assert mov.quantity == bought_qty
        assert mov.previous_stock == initial_stock
        assert mov.new_stock == expected_stock
        assert mov.reference_id == order_data["id"]

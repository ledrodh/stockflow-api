"""Integration tests for the Stock Reconciliation Engine and GET /api/v1/inventory/reconcile."""

from decimal import Decimal
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from stockflow.models.inventory import InventoryMovement, MovementType
from stockflow.models.product import Product
from stockflow.services.reconciliation_service import run_inventory_reconciliation


async def test_reconciliation_endpoint_requires_admin_role(
    client: AsyncClient,
    admin_headers: dict[str, str],
    customer_headers: dict[str, str],
) -> None:
    """Verify GET /api/v1/inventory/reconcile enforces RBAC (Admin only)."""
    # 1. Unauthenticated request -> 401
    unauth_resp = await client.get("/api/v1/inventory/reconcile")
    assert unauth_resp.status_code == 401

    # 2. Customer request -> 403
    cust_resp = await client.get("/api/v1/inventory/reconcile", headers=customer_headers)
    assert cust_resp.status_code == 403

    # 3. Admin request -> 200 OK
    admin_resp = await client.get("/api/v1/inventory/reconcile", headers=admin_headers)
    assert admin_resp.status_code == 200
    data = admin_resp.json()
    assert data["snapshot_isolation_level"] == "REPEATABLE READ, READ ONLY"
    assert "is_consistent" in data
    assert "total_products_checked" in data


async def test_reconciliation_verifies_consistent_product_lifecycle(
    client: AsyncClient,
    admin_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    """Verify product creation, restock, and purchase produce 100% consistent ledger."""
    # 1. Create product with initial stock 10 (creates OPENING movement seq 1)
    prod_resp = await client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={
            "sku": "RECON-CLEAN-01",
            "name": "Reconciliation Test Item",
            "price": "100.00",
            "stock_quantity": 10,
            "min_stock": 2,
        },
    )
    assert prod_resp.status_code == 201
    product_id = prod_resp.json()["id"]

    # 2. Add restock movement (IN seq 2, +15)
    move_resp = await client.post(
        "/api/v1/inventory/movements",
        headers=admin_headers,
        json={
            "product_id": product_id,
            "type": "IN",
            "quantity": 15,
            "reason": "Restock batch A",
        },
    )
    assert move_resp.status_code == 201

    # 3. Create purchase order (OUT seq 3, -5)
    idempotency_key = f"recon-order-{uuid4()}"
    order_resp = await client.post(
        "/api/v1/orders",
        headers={**admin_headers, "Idempotency-Key": idempotency_key},
        json={"items": [{"product_id": product_id, "quantity": 5}]},
    )
    assert order_resp.status_code == 201

    # Run reconciliation service directly
    report = await run_inventory_reconciliation(db_session)
    assert report.is_consistent is True
    assert report.total_products_checked >= 1
    assert report.discrepant_products_count == 0


async def test_reconciliation_detects_sequence_gap_and_arithmetic_discrepancy(
    db_session: AsyncSession,
) -> None:
    """Verify corrupted movement sequences or stock levels are caught by reconciliation."""
    # Create product directly
    product = Product(
        sku="RECON-CORRUPT-01",
        name="Corrupted Product",
        price=Decimal("50.00"),
        stock_quantity=20,  # Deliberately mismatched stock
        min_stock=5,
        is_active=True,
    )
    db_session.add(product)
    await db_session.flush()

    # Disable immutable trigger temporarily to inject corrupt sequence for test assertion
    await db_session.execute(
        text("ALTER TABLE inventory_movements DISABLE TRIGGER trg_immutable_inventory_movements;")
    )

    # Insert movement with sequence gap (sequence 1, then sequence 3 instead of 2)
    m1 = InventoryMovement(
        product_id=product.id,
        movement_sequence=1,
        type=MovementType.OPENING.value,
        quantity=10,
        previous_stock=0,
        new_stock=10,
        reason="Opening stock",
    )
    m2 = InventoryMovement(
        product_id=product.id,
        movement_sequence=3,  # Sequence gap! (Missing 2)
        type=MovementType.IN.value,
        quantity=5,
        previous_stock=10,
        new_stock=15,
        reason="Restock gap",
    )
    db_session.add_all([m1, m2])
    await db_session.flush()

    await db_session.execute(
        text("ALTER TABLE inventory_movements ENABLE TRIGGER trg_immutable_inventory_movements;")
    )
    await db_session.commit()

    report = await run_inventory_reconciliation(db_session)
    assert report.is_consistent is False
    assert report.discrepant_products_count >= 1

    corrupt_entry = next(d for d in report.discrepancies if d.sku == "RECON-CORRUPT-01")
    assert corrupt_entry.is_consistent is False
    # Verified sequence error
    assert any(
        "Expected sequence 2 but found sequence 3" in err for err in corrupt_entry.sequence_errors
    )
    # Verified arithmetic mismatch: stock_quantity is 20, ledger sum is 15 -> delta = 5
    assert corrupt_entry.current_stock_quantity == 20
    assert corrupt_entry.calculated_ledger_stock == 15
    assert corrupt_entry.discrepancy_delta == 5

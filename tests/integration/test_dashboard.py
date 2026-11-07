"""Integration tests for dashboard summary metrics and activity feeds."""

from httpx import AsyncClient


async def test_get_dashboard_summary_metrics(
    client: AsyncClient,
    admin_headers: dict[str, str],
    customer_headers: dict[str, str],
) -> None:
    """Verify aggregated metrics for products, stock units, orders, and revenue."""
    # 1. Create 2 products
    p1 = (
        await client.post(
            "/api/v1/products",
            headers=admin_headers,
            json={
                "sku": "DASH-P1",
                "name": "Dashboard Product 1",
                "price": "100.00",
                "stock_quantity": 10,
            },
        )
    ).json()

    await client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={
            "sku": "DASH-P2",
            "name": "Dashboard Low Stock Item",
            "price": "50.00",
            "stock_quantity": 2,  # Low stock (< 5)
        },
    )

    # 2. Place an order
    await client.post(
        "/api/v1/orders",
        headers={**customer_headers, "Idempotency-Key": "dash-order-01"},
        json={
            "items": [
                {"product_id": p1["id"], "quantity": 3},
            ]
        },
    )

    # 3. Query dashboard summary
    summary_resp = await client.get("/api/v1/dashboard/summary", headers=customer_headers)
    assert summary_resp.status_code == 200
    data = summary_resp.json()

    assert data["total_products"] == 2
    # Stock remaining: (10 - 3) + 2 = 9 units
    assert data["total_stock_items"] == 9
    assert data["low_stock_products"] == 1
    assert data["total_orders"] == 1
    assert data["total_revenue"] == "300.00"
    assert len(data["recent_orders"]) == 1
    assert len(data["recent_movements"]) >= 3  # Initial stock movements + purchase OUT

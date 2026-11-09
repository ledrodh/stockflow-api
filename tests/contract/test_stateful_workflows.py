"""Stateful tests: Modalidade A (Workflow Deterministico Encadeado)
e Modalidade B (State Machine Schemathesis).
"""

import os
import uuid
from typing import Any

import pytest
import schemathesis
from httpx import AsyncClient

from stockflow.core.config import settings
from stockflow.main import app
from stockflow.models.user import User

# Configure test database URL for ASGI state machine
_test_host = "127.0.0.1" if settings.POSTGRES_HOST == "localhost" else settings.POSTGRES_HOST
os.environ["DATABASE_URL"] = (
    f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
    f"@{_test_host}:{settings.POSTGRES_PORT}/stockflow_test_db"
)

schema = schemathesis.openapi.from_asgi("/openapi.json", app)

# Modalidade B: Stateful Testing nativo do Schemathesis baseado em maquina de estados
BaseAPIWorkflow = schema.as_state_machine()


class CustomAPIWorkflow(BaseAPIWorkflow):  # type: ignore[misc, valid-type]
    """Modalidade B: Maquina de estados nativa do Schemathesis.

    Executa geracao estocastica de transicoes de operacoes. Valida que nenhum
    passo gere HTTP 5xx (Server Error), tolerando respostas de autenticacao (401/403)
    e validacao de contrato da API.
    """

    def validate_response(
        self,
        response: Any,
        case: Any,
        additional_checks: Any = None,
        **kwargs: Any,
    ) -> None:
        assert response.status_code < 500, (
            f"Stateful transition triggered server error HTTP {response.status_code} "
            f"on {case.method.upper()} {case.path}: {response.text}"
        )


TestNativeSchemathesisStateful = CustomAPIWorkflow.TestCase


@pytest.mark.asyncio
async def test_deterministic_e2e_stateful_lifecycle_workflow(
    client: AsyncClient,
    admin_headers: dict[str, str],
    customer_headers: dict[str, str],
    admin_user: User,
    customer_user: User,
) -> None:
    """Modalidade A: Workflow deterministico encadeado de ciclo de vida completo:

    1. Admin creates a new product via POST /api/v1/products.
    2. Customer retrieves product details via GET /api/v1/products/{product_id}.
    3. Admin checks initial inventory ledger via GET /api/v1/inventory/movements.
    4. Admin adjusts stock via POST /api/v1/inventory/movements (ADJUSTMENT).
    5. Customer places an atomic order via POST /api/v1/orders with Idempotency-Key.
    6. Customer repeats the identical request with same key (asserting exact replay).
    7. Customer fetches the order via GET /api/v1/orders/{order_id}.
    8. Customer cancels order via POST /api/v1/orders/{order_id}/cancel.
    9. Admin runs automated reconciliation via GET /api/v1/inventory/reconcile.
    """
    # Step 1: Admin creates a product
    unique_suffix = uuid.uuid4().hex[:8]
    sku = f"STF-{unique_suffix}".upper()
    create_payload = {
        "sku": sku,
        "name": f"Stateful Test Product {unique_suffix}",
        "description": "Product created during Schemathesis stateful lifecycle audit",
        "price": "149.90",
        "stock_quantity": 50,
        "min_stock": 5,
    }
    res_create = await client.post(
        "/api/v1/products",
        json=create_payload,
        headers=admin_headers,
    )
    assert res_create.status_code == 201, f"Product creation failed: {res_create.text}"
    product_data = res_create.json()
    product_id = product_data["id"]
    assert product_data["sku"] == sku
    assert product_data["stock_quantity"] == 50

    # Step 2: Customer retrieves product details
    res_get = await client.get(
        f"/api/v1/products/{product_id}",
        headers=customer_headers,
    )
    assert res_get.status_code == 200
    assert res_get.json()["id"] == product_id

    # Step 3: Admin inspects inventory ledger
    res_ledger = await client.get(
        f"/api/v1/inventory/movements?product_id={product_id}",
        headers=admin_headers,
    )
    assert res_ledger.status_code == 200
    movements = res_ledger.json()["items"]
    assert len(movements) >= 1
    assert movements[0]["type"] == "OPENING"
    assert movements[0]["movement_sequence"] == 1

    # Step 4: Admin adds stock via movement
    res_adjust = await client.post(
        "/api/v1/inventory/movements",
        json={
            "product_id": product_id,
            "type": "ADJUSTMENT",
            "adjustment_direction": "INCREASE",
            "quantity": 25,
            "reason": "Schemathesis stateful warehouse restocking",
        },
        headers=admin_headers,
    )
    assert res_adjust.status_code == 201
    assert res_adjust.json()["new_stock"] == 75

    # Step 5: Customer places an atomic order with Idempotency-Key
    idempotency_key = str(uuid.uuid4())
    order_payload = {
        "items": [
            {
                "product_id": product_id,
                "quantity": 10,
            }
        ]
    }
    res_order = await client.post(
        "/api/v1/orders",
        json=order_payload,
        headers={**customer_headers, "Idempotency-Key": idempotency_key},
    )
    assert res_order.status_code == 201, f"Order placement failed: {res_order.text}"
    order_data = res_order.json()
    order_id = order_data["id"]
    assert order_data["status"] == "CONFIRMED"
    assert order_data["total_amount"] == "1499.00"

    # Step 6: Customer retries identical request (persistent idempotency check)
    res_retry = await client.post(
        "/api/v1/orders",
        json=order_payload,
        headers={**customer_headers, "Idempotency-Key": idempotency_key},
    )
    assert res_retry.status_code == 201
    assert res_retry.json()["id"] == order_id  # Exactly the same order returned

    # Step 7: Customer fetches order by ID
    res_fetch = await client.get(
        f"/api/v1/orders/{order_id}",
        headers=customer_headers,
    )
    assert res_fetch.status_code == 200
    assert res_fetch.json()["id"] == order_id

    # Step 8: Customer cancels order (stock should be automatically restored)
    res_cancel = await client.post(
        f"/api/v1/orders/{order_id}/cancel",
        headers=customer_headers,
    )
    assert res_cancel.status_code == 200
    assert res_cancel.json()["status"] == "CANCELLED"

    # Step 9: Verify restored stock on product
    res_product_after = await client.get(f"/api/v1/products/{product_id}")
    assert res_product_after.status_code == 200
    assert res_product_after.json()["stock_quantity"] == 75

    # Step 10: Admin executes ledger reconciliation audit
    res_reconcile = await client.get(
        f"/api/v1/inventory/reconcile?product_id={product_id}",
        headers=admin_headers,
    )
    assert res_reconcile.status_code == 200
    reconcile_report = res_reconcile.json()
    assert reconcile_report["is_consistent"] is True
    assert len(reconcile_report["discrepancies"]) == 0

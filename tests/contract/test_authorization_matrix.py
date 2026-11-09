"""Comprehensive authentication and authorization (RBAC & Tenant Isolation) matrix tests."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from stockflow.core.security import create_access_token, get_password_hash
from stockflow.models.user import User, UserRole


@pytest.fixture
async def second_customer_user(db_session: AsyncSession) -> User:
    """Create a distinct second customer to test tenant isolation and anti-IDOR protections."""
    user = User(
        email="second.customer@stockflow.io",
        hashed_password=get_password_hash("SecondCustomerSecret#2026"),
        full_name="Second Customer",
        role=UserRole.CUSTOMER.value,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def second_customer_headers(second_customer_user: User) -> dict[str, str]:
    """Return authorization header for the second customer."""
    token = create_access_token(subject=second_customer_user.id, role=second_customer_user.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_auth_matrix_unauthenticated_endpoints_return_401(
    client: AsyncClient,
) -> None:
    """Matrix Row 1: Requests without credentials to protected endpoints must return 401."""
    protected_urls = [
        ("GET", "/api/v1/auth/me"),
        ("POST", "/api/v1/orders"),
        ("GET", "/api/v1/orders"),
        ("GET", "/api/v1/dashboard/summary"),
        ("POST", "/api/v1/inventory/movements"),
        ("GET", "/api/v1/inventory/reconcile"),
    ]

    for method, url in protected_urls:
        res = await client.request(method, url)
        assert res.status_code == 401, f"{method} {url} returned {res.status_code} instead of 401."
        assert res.json()["error"]["code"] == "AUTHENTICATION_FAILED"


@pytest.mark.asyncio
async def test_auth_matrix_invalid_or_expired_token_returns_401(
    client: AsyncClient,
) -> None:
    """Matrix Row 2: Malformed, forged, or expired tokens must return 401."""
    invalid_headers_list = [
        {"Authorization": "Bearer malformed.invalid.token"},
        {"Authorization": "Bearer "},
        {"Authorization": "InvalidScheme token"},
    ]

    for headers in invalid_headers_list:
        res = await client.get("/api/v1/auth/me", headers=headers)
        assert (
            res.status_code == 401
        ), f"Headers {headers} returned {res.status_code} instead of 401."
        assert res.json()["error"]["code"] == "AUTHENTICATION_FAILED"


@pytest.mark.asyncio
async def test_auth_matrix_customer_forbidden_on_admin_operations(
    client: AsyncClient,
    customer_headers: dict[str, str],
) -> None:
    """Matrix Row 3: Customers attempting Admin-only operations
    must strictly receive 403 Forbidden.
    """
    random_uuid = str(uuid.uuid4())
    admin_only_calls = [
        ("POST", "/api/v1/products", {"sku": "FORBID-1", "name": "Test", "price": "10.00"}),
        ("PATCH", f"/api/v1/products/{random_uuid}", {"name": "Updated"}),
        ("DELETE", f"/api/v1/products/{random_uuid}", None),
        ("POST", "/api/v1/inventory/movements", {"product_id": random_uuid, "quantity": 10}),
        ("GET", "/api/v1/inventory/reconcile", None),
        ("GET", "/api/v1/dashboard/summary", None),
        ("POST", "/api/v1/dashboard/maintenance/cleanup-idempotency", None),
    ]

    for method, url, payload in admin_only_calls:
        res = await client.request(method, url, json=payload, headers=customer_headers)
        assert (
            res.status_code == 403
        ), f"RBAC Violation: Customer on {method} {url} returned {res.status_code} instead of 403."
        assert res.json()["error"]["code"] == "PERMISSION_DENIED"


@pytest.mark.asyncio
async def test_auth_matrix_admin_allowed_on_admin_operations(
    client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Matrix Row 4: Admins must succeed on authorized administrative operations."""
    res_dash = await client.get("/api/v1/dashboard/summary", headers=admin_headers)
    assert res_dash.status_code == 200
    assert "total_products" in res_dash.json()

    res_rec = await client.get("/api/v1/inventory/reconcile", headers=admin_headers)
    assert res_rec.status_code == 200
    assert "is_consistent" in res_rec.json()


@pytest.mark.asyncio
async def test_auth_matrix_customer_isolation_and_anti_idor(
    client: AsyncClient,
    customer_headers: dict[str, str],
    second_customer_headers: dict[str, str],
    admin_headers: dict[str, str],
) -> None:
    """Matrix Row 5 & 6: Tenant/Customer Isolation & Anti-IDOR:

    - Customer A creates an order.
    - Customer A can fetch their own order (HTTP 200).
    - Customer B attempts to fetch Customer A's order -> Denied (HTTP 404 to prevent IDOR leak).
    - Customer B attempts to cancel Customer A's order -> Denied (HTTP 404).
    - Customer B listing orders does not see Customer A's order in their list.
    - Admin can view Customer A's order (HTTP 200).
    """
    # 1. Admin creates product with stock
    sku = f"ISO-{uuid.uuid4().hex[:6]}".upper()
    prod_res = await client.post(
        "/api/v1/products",
        json={
            "sku": sku,
            "name": f"Isolation Test Product {sku}",
            "price": "50.00",
            "stock_quantity": 20,
        },
        headers=admin_headers,
    )
    assert prod_res.status_code == 201
    product_id = prod_res.json()["id"]

    # 2. Customer A places an order
    order_res = await client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": product_id, "quantity": 2}]},
        headers={**customer_headers, "Idempotency-Key": str(uuid.uuid4())},
    )
    assert order_res.status_code == 201
    order_id = order_res.json()["id"]

    # 3. Customer A accesses their own order -> 200 OK
    own_res = await client.get(f"/api/v1/orders/{order_id}", headers=customer_headers)
    assert own_res.status_code == 200
    assert own_res.json()["id"] == order_id

    # 4. Customer B tries to access Customer A's order -> 404 (anti-IDOR protection)
    alien_res = await client.get(f"/api/v1/orders/{order_id}", headers=second_customer_headers)
    assert alien_res.status_code == 404, f"IDOR Vulnerability: Customer B accessed {order_id}"
    assert alien_res.json()["error"]["code"] == "RESOURCE_NOT_FOUND"

    # 5. Customer B tries to cancel Customer A's order -> 403 (Permission Denied)
    alien_cancel = await client.post(
        f"/api/v1/orders/{order_id}/cancel", headers=second_customer_headers
    )
    assert alien_cancel.status_code == 403, f"IDOR Vulnerability: Customer B cancelled {order_id}"
    assert alien_cancel.json()["error"]["code"] == "PERMISSION_DENIED"

    # 6. Customer B lists orders -> 0 orders listed
    list_b = await client.get("/api/v1/orders", headers=second_customer_headers)
    assert list_b.status_code == 200
    assert list_b.json()["total"] == 0

    # 7. Admin accesses Customer A's order -> 200 OK
    admin_access = await client.get(f"/api/v1/orders/{order_id}", headers=admin_headers)
    assert admin_access.status_code == 200
    assert admin_access.json()["id"] == order_id

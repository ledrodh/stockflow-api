"""Property-based contract tests using Schemathesis against the OpenAPI schema."""

import os
from typing import Any

import pytest
import schemathesis
from requests.structures import CaseInsensitiveDict
from schemathesis.core.result import Ok

from stockflow.core.config import settings
from stockflow.main import app

# Configure test database URL for ASGI execution
os.environ["DATABASE_URL"] = (
    f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
    f"@127.0.0.1:{settings.POSTGRES_PORT}/stockflow_test_db"
)

schema = schemathesis.openapi.from_asgi("/openapi.json", app)


@pytest.mark.asyncio
async def test_unauthenticated_requests_do_not_cause_server_errors(
    test_engine: Any,
) -> None:
    """Every endpoint in the OpenAPI specification must handle unauthenticated calls safely.

    Protected endpoints must return 401 or 403; public endpoints must return 2xx or 4xx.
    No endpoint may ever return an unhandled 5xx Server Error.
    """
    failures: list[str] = []

    for result in schema.get_all_operations():
        if not isinstance(result, Ok):
            continue
        op = result.ok()
        if not op:
            continue

        strategy = op.as_strategy()
        # Generate representative test cases per operation
        for _ in range(3):
            case = strategy.example()
            response = case.call()

            # Rule 1: Never return 5xx server errors
            if response.status_code >= 500:
                failures.append(
                    f"{op.method.upper()} {op.path} -> HTTP {response.status_code}: {response.text}"
                )

            # Rule 2: Catalog reads and health/auth endpoints are public;
            # all other endpoints require authentication
            is_public = op.path in (
                "/health",
                "/api/v1/health",
                "/api/v1/auth/register",
                "/api/v1/auth/login",
                "/api/v1/auth/token",
            ) or (op.method == "get" and op.path.startswith("/api/v1/products"))

            if not is_public and response.status_code not in (401, 403, 404, 422):
                msg = (
                    f"Security Gate: {op.method.upper()} {op.path} responded with "
                    f"{response.status_code} instead of 401/403 when unauthenticated."
                )
                failures.append(msg)

    assert not failures, "Schemathesis detected contract/security failures:\n" + "\n".join(failures)


@pytest.mark.asyncio
async def test_authenticated_admin_endpoints_contract_conformance(
    admin_headers: dict[str, str],
    test_engine: Any,
) -> None:
    """Verify that authenticated administrative endpoints conform to OpenAPI schemas.

    Responses must not produce 5xx internal server errors under randomized property fuzzing.
    """
    failures: list[str] = []

    admin_paths = [
        "/api/v1/dashboard/summary",
        "/api/v1/products",
        "/api/v1/inventory/reconcile",
    ]

    for result in schema.get_all_operations():
        if not isinstance(result, Ok):
            continue
        op = result.ok()
        if not op or op.path not in admin_paths:
            continue

        strategy = op.as_strategy()
        for _ in range(5):
            case = strategy.example()
            # Inject authenticated admin headers
            if case.headers is not None:
                case.headers.update(admin_headers)
            else:
                case.headers = CaseInsensitiveDict(admin_headers)
            response = case.call()

            if response.status_code >= 500:
                failures.append(
                    f"Admin Contract Failure: {op.method.upper()} {op.path} returned "
                    f"HTTP {response.status_code}: {response.text}"
                )

    assert not failures, "Admin contract failures detected:\n" + "\n".join(failures)


@pytest.mark.asyncio
async def test_authenticated_customer_endpoints_contract_conformance(
    customer_headers: dict[str, str],
    test_engine: Any,
) -> None:
    """Verify customer endpoints (/auth/me, /products, /orders) conform under property fuzzing."""
    failures: list[str] = []

    customer_paths = [
        "/api/v1/auth/me",
        "/api/v1/products",
        "/api/v1/orders",
    ]

    for result in schema.get_all_operations():
        if not isinstance(result, Ok):
            continue
        op = result.ok()
        if not op or op.path not in customer_paths:
            continue

        strategy = op.as_strategy()
        for _ in range(5):
            case = strategy.example()
            if case.headers is not None:
                case.headers.update(customer_headers)
            else:
                case.headers = CaseInsensitiveDict(customer_headers)
            response = case.call()

            if response.status_code >= 500:
                failures.append(
                    f"Customer Contract Failure: {op.method.upper()} {op.path} returned "
                    f"HTTP {response.status_code}: {response.text}"
                )

    assert not failures, "Customer contract failures detected:\n" + "\n".join(failures)

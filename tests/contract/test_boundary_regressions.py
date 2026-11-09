"""Regression tests for boundary and input fuzzing issues discovered by Schemathesis in Phase 4."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_regression_huge_offset_boundary_returns_422_instead_of_500(
    client: AsyncClient,
    customer_headers: dict[str, str],
    admin_headers: dict[str, str],
) -> None:
    """Discovered by Schemathesis: Unbounded offset (> bigint max)
    previously crashed PostgreSQL with 500.

    Ensures that extreme offset values are rejected at the FastAPI schema boundary with HTTP 422.
    """
    huge_offset = 54555461087354165395456

    test_cases = [
        (f"/api/v1/products?offset={huge_offset}", {}),
        (f"/api/v1/orders?offset={huge_offset}", customer_headers),
        (f"/api/v1/inventory/movements?offset={huge_offset}", admin_headers),
    ]

    for url, headers in test_cases:
        res = await client.get(url, headers=headers)
        assert res.status_code == 422, (
            f"Endpoint {url} returned HTTP {res.status_code} instead of 422 for huge offset. "
            f"Response body: {res.text}"
        )
        assert res.status_code != 500, f"Critical: 500 Internal Server Error returned for {url}"


@pytest.mark.asyncio
async def test_regression_nul_byte_in_search_does_not_crash_database(
    client: AsyncClient,
) -> None:
    """Discovered by Schemathesis: NUL byte (\\x00) in search queries
    previously triggered untranslatable character 500 database error.

    Ensures that search inputs with NUL bytes are rejected at the FastAPI schema boundary
    with HTTP 422 Unprocessable Content, avoiding semantic mutations.
    """
    res = await client.get("/api/v1/products?search=test%00null")
    assert res.status_code == 422, (
        f"Search with NUL byte returned HTTP {res.status_code} instead of 422. "
        f"Response body: {res.text}"
    )
    assert res.status_code != 500, "Critical: 500 Database Error triggered by NUL byte in search"

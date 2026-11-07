"""Integration tests for health checks, user registration, JWT auth, and RBAC safety."""

from httpx import AsyncClient


async def test_health_check_verifies_real_database_connection(client: AsyncClient) -> None:
    """GET /health must execute a real database query and return connected status."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


async def test_user_registration_and_login_flow(client: AsyncClient) -> None:
    """Register a user, verify role defaults to customer, login, and fetch /auth/me."""
    reg_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "Alice.Engineer@StockFlow.io",
            "password": "SecurePassword123!",
            "full_name": "Alice Engineer",
        },
    )
    assert reg_response.status_code == 201
    user_data = reg_response.json()
    assert user_data["email"] == "alice.engineer@stockflow.io"
    assert user_data["role"] == "customer"
    assert user_data["is_active"] is True
    assert "hashed_password" not in user_data

    # Duplicate email must return 409 Conflict
    dup_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "alice.engineer@stockflow.io",
            "password": "AnotherPassword123!",
            "full_name": "Alice Duplicate",
        },
    )
    assert dup_response.status_code == 409
    assert dup_response.json()["error"]["code"] == "RESOURCE_CONFLICT"

    # Login with valid credentials
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "alice.engineer@stockflow.io",
            "password": "SecurePassword123!",
        },
    )
    assert login_response.status_code == 200
    token_data = login_response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

    # Access protected /me endpoint
    me_response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token_data['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["id"] == user_data["id"]


async def test_registration_rejects_privilege_escalation_payload(client: AsyncClient) -> None:
    """Passing 'role': 'admin' in public registration must be rejected with 422."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "attacker@stockflow.io",
            "password": "AttackerPassword123!",
            "full_name": "Attacker User",
            "role": "admin",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_unauthenticated_and_invalid_credentials_return_401(client: AsyncClient) -> None:
    """Missing or invalid tokens and wrong login passwords must return 401 Unauthorized."""
    unauth_me = await client.get("/api/v1/auth/me")
    assert unauth_me.status_code == 401

    invalid_token_me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.jwt.token"},
    )
    assert invalid_token_me.status_code == 401

    bad_login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "nonexistent@stockflow.io",
            "password": "WrongPassword123!",
        },
    )
    assert bad_login.status_code == 401

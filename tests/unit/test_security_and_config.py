"""Unit tests for password hashing (pwdlib/Argon2), JWT security, and Pydantic settings."""

from datetime import timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from stockflow.core.config import Settings
from stockflow.core.exceptions import AuthenticationError
from stockflow.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from stockflow.schemas.order import OrderCreate, OrderItemCreate
from stockflow.services.order_service import compute_order_request_hash


def test_argon2_password_hashing_and_verification() -> None:
    """Ensure pwdlib Argon2 produces salted hashes and verifies accurately."""
    raw_password = "SuperStrongPassword!2026"
    hashed = get_password_hash(raw_password)

    assert hashed.startswith("$argon2id$")
    assert verify_password(raw_password, hashed) is True
    assert verify_password("WrongPassword!2026", hashed) is False


def test_jwt_create_and_decode_token() -> None:
    """Verify JWT access token encoding and decoding."""
    user_id = uuid4()
    token = create_access_token(subject=user_id, role="admin")
    payload = decode_access_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["role"] == "admin"


def test_jwt_expired_token_raises_authentication_error() -> None:
    """Verify expired tokens raise AuthenticationError (401)."""
    user_id = uuid4()
    expired_token = create_access_token(
        subject=user_id,
        role="customer",
        expires_delta=timedelta(seconds=-10),
    )
    with pytest.raises(AuthenticationError, match="expired"):
        decode_access_token(expired_token)


def test_settings_prohibits_sqlite_database_url() -> None:
    """Ensure SQLite URLs are explicitly rejected by Settings validation."""
    with pytest.raises(ValidationError, match="prohibited"):
        Settings(DATABASE_URL="sqlite+aiosqlite:///./test.db")


def test_settings_rejects_insecure_secrets_and_defaults_in_production() -> None:
    """Ensure production environment strictly rejects default or blacklisted secrets."""
    with pytest.raises(ValidationError, match="cannot use known insecure or default keys"):
        Settings(
            _env_file=None,
            APP_ENV="production",
            SECRET_KEY="stockflow-dev-secret-jwt-key-safe-for-local-dev-only-2026",
            POSTGRES_PASSWORD="secure_prod_password_987!",
        )

    with pytest.raises(ValidationError, match="cannot use known insecure or default keys"):
        Settings(
            _env_file=None,
            APP_ENV="production",
            SECRET_KEY="change-this-super-secret-jwt-key-in-production-min-32-chars",
            POSTGRES_PASSWORD="secure_prod_password_987!",
        )

    with pytest.raises(ValidationError, match="cannot use the default development password"):
        Settings(
            _env_file=None,
            APP_ENV="production",
            SECRET_KEY="a-very-strong-production-secret-token-key-2026",
            POSTGRES_PASSWORD="stockflow_secret_password",
        )


def test_settings_accepts_valid_production_configuration() -> None:
    """Ensure properly configured production settings pass validation."""
    valid_prod = Settings(
        _env_file=None,
        APP_ENV="production",
        SECRET_KEY="super-secure-production-random-token-min-32-chars-value!",
        POSTGRES_PASSWORD="strong_production_password_2026#",
        POSTGRES_HOST="db.internal.stockflow.io",
        POSTGRES_DB="stockflow_production_db",
    )
    assert valid_prod.APP_ENV == "production"
    assert (
        valid_prod.SECRET_KEY.get_secret_value()
        == "super-secure-production-random-token-min-32-chars-value!"
    )


def test_compute_order_request_hash_is_order_independent() -> None:
    """Verify canonical order request hash is deterministic regardless of item list order."""
    prod_a = uuid4()
    prod_b = uuid4()

    order_1 = OrderCreate(
        items=[
            OrderItemCreate(product_id=prod_a, quantity=2),
            OrderItemCreate(product_id=prod_b, quantity=5),
        ]
    )
    order_2 = OrderCreate(
        items=[
            OrderItemCreate(product_id=prod_b, quantity=5),
            OrderItemCreate(product_id=prod_a, quantity=2),
        ]
    )

    assert compute_order_request_hash(order_1) == compute_order_request_hash(order_2)

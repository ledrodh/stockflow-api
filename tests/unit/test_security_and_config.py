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
    with pytest.raises(ValidationError, match="SQLite is strictly prohibited"):
        Settings(DATABASE_URL="sqlite+aiosqlite:///./test.db")


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

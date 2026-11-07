"""Pytest fixtures configured strictly against a real PostgreSQL instance (SQLite is forbidden)."""

import os
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from stockflow.core.config import settings
from stockflow.core.security import create_access_token, get_password_hash
from stockflow.db.base import Base
from stockflow.db.session import get_db_session
from stockflow.main import app
from stockflow.models.user import User, UserRole

DEFAULT_TEST_DB_URL = (
    f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
    f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/stockflow_test_db"
)
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", DEFAULT_TEST_DB_URL)

if "sqlite" in TEST_DATABASE_URL.lower():
    raise RuntimeError("SQLite is strictly prohibited for StockFlow API tests. Use PostgreSQL.")

_SCHEMA_INITIALIZED = False


async def _ensure_schema_initialized(engine: AsyncEngine) -> None:
    """Initialize PostgreSQL tables and triggers once per test session."""
    global _SCHEMA_INITIALIZED
    if _SCHEMA_INITIALIZED:
        return

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text(
                """
                CREATE OR REPLACE FUNCTION prevent_inventory_movement_mutation()
                RETURNS TRIGGER AS $$
                BEGIN
                    RAISE EXCEPTION 'inventory_movements table is append-only and immutable.';
                END;
                $$ LANGUAGE plpgsql;
                """
            )
        )
        await conn.execute(
            text("DROP TRIGGER IF EXISTS trg_immutable_inventory_movements ON inventory_movements;")
        )
        await conn.execute(
            text(
                """
                CREATE TRIGGER trg_immutable_inventory_movements
                BEFORE UPDATE OR DELETE ON inventory_movements
                FOR EACH ROW EXECUTE FUNCTION prevent_inventory_movement_mutation();
                """
            )
        )
    _SCHEMA_INITIALIZED = True


@pytest.fixture
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create a function-scoped AsyncEngine bound to the active test's event loop."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=25,
        max_overflow=25,
    )
    await _ensure_schema_initialized(engine)

    async with engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE TABLE idempotency_keys, inventory_movements, "
                "order_items, orders, products, users RESTART IDENTITY CASCADE;"
            )
        )

    yield engine
    await engine.dispose()


@pytest.fixture
def test_session_maker(test_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Return an async_sessionmaker bound to the current test's PostgreSQL engine."""
    return async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


@pytest.fixture
async def db_session(
    test_session_maker: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """Yield a standalone AsyncSession for direct database assertions in tests."""
    async with test_session_maker() as session:
        yield session


@pytest.fixture
async def client(
    test_session_maker: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncClient, None]:
    """Provide an httpx.AsyncClient wired to the FastAPI app with overridden DB session."""

    async def _override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        async with test_session_maker() as session:
            yield session

    app.dependency_overrides[get_db_session] = _override_get_db_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client
    app.dependency_overrides.clear()


@pytest.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Seed an internal administrator user directly in PostgreSQL."""
    admin = User(
        email="admin@stockflow.io",
        hashed_password=get_password_hash("AdminSecret#2026"),
        full_name="System Administrator",
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest.fixture
def admin_headers(admin_user: User) -> dict[str, str]:
    """Return Authorization headers for the seeded admin user."""
    token = create_access_token(subject=admin_user.id, role=admin_user.role)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def customer_user(db_session: AsyncSession) -> User:
    """Seed a standard customer user directly in PostgreSQL."""
    customer = User(
        email="customer@stockflow.io",
        hashed_password=get_password_hash("CustomerSecret#2026"),
        full_name="Regular Customer",
        role=UserRole.CUSTOMER.value,
        is_active=True,
    )
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)
    return customer


@pytest.fixture
def customer_headers(customer_user: User) -> dict[str, str]:
    """Return Authorization headers for the seeded customer user."""
    token = create_access_token(subject=customer_user.id, role=customer_user.role)
    return {"Authorization": f"Bearer {token}"}

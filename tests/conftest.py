"""Pytest fixtures configured strictly against a real PostgreSQL instance (SQLite is forbidden)."""

import asyncio
import os
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from stockflow.core.config import settings
from stockflow.core.security import create_access_token, get_password_hash
from stockflow.db.session import get_db_session
from stockflow.main import app
from stockflow.models.user import User, UserRole

_test_host = "127.0.0.1" if settings.POSTGRES_HOST == "localhost" else settings.POSTGRES_HOST
DEFAULT_TEST_DB_URL = (
    f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
    f"@{_test_host}:{settings.POSTGRES_PORT}/stockflow_test_db"
)
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", DEFAULT_TEST_DB_URL)

parsed_test_url = make_url(TEST_DATABASE_URL)
if parsed_test_url.get_backend_name() != "postgresql":
    raise RuntimeError(
        f"Backend '{parsed_test_url.get_backend_name()}' is prohibited. Tests require PostgreSQL."
    )

# Safety guard: Prevent accidental data loss against non-test databases
_target_db_name = (parsed_test_url.database or "").lower()
if "test" not in _target_db_name:
    raise RuntimeError(
        f"SAFETY GUARD: Destructive test schema reset refused. Database name '{_target_db_name}' "
        "must explicitly contain 'test' (e.g., 'stockflow_test_db')."
    )

if settings.APP_ENV == "production":
    raise RuntimeError("SAFETY GUARD: Tests cannot be executed against production environment.")

if os.getenv("ALLOW_DESTRUCTIVE_TEST_RESET", "true").lower() not in ("true", "1", "yes"):
    raise RuntimeError(
        "SAFETY GUARD: Destructive test reset refused. "
        "ALLOW_DESTRUCTIVE_TEST_RESET=true is required."
    )

_SCHEMA_INITIALIZED = False


def _run_alembic_migrations(db_url: str) -> None:
    """Run real Alembic migrations to head in a background worker thread."""
    os.environ["ALEMBIC_DATABASE_URL"] = db_url
    project_root = Path(__file__).resolve().parent.parent
    alembic_cfg = Config(str(project_root / "alembic.ini"))
    alembic_cfg.set_main_option(
        "script_location", str(project_root / "src" / "stockflow" / "db" / "migrations")
    )
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(alembic_cfg, "head")


async def _ensure_schema_initialized(engine: AsyncEngine) -> None:
    """Initialize PostgreSQL tables strictly through real Alembic migrations."""
    global _SCHEMA_INITIALIZED
    if _SCHEMA_INITIALIZED:
        return

    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))

    await asyncio.to_thread(_run_alembic_migrations, TEST_DATABASE_URL)
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

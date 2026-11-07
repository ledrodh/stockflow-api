"""FastAPI application entrypoint for StockFlow API."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from stockflow import __version__
from stockflow.api.v1.endpoints import health
from stockflow.api.v1.router import v1_router
from stockflow.core.config import settings
from stockflow.core.exceptions import register_exception_handlers
from stockflow.db.session import engine


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and graceful shutdown resources."""
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application instance."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=__version__,
        description=(
            "High-integrity inventory and order management engine with atomic transactions, "
            "database-level concurrency control (SELECT FOR UPDATE), PostgreSQL idempotency, "
            "and an immutable inventory movement ledger."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    # Root-level /health endpoint as specified in Sprint 1
    app.include_router(health.router)
    # Versioned /api/v1 endpoints
    app.include_router(v1_router, prefix=settings.API_V1_PREFIX)
    # Unprefixed fallback routes (hidden from OpenAPI docs to avoid duplication)
    app.include_router(v1_router, include_in_schema=False)

    return app


app = create_app()

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
            "and an append-only inventory movement ledger."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Restrictive CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
    )

    register_exception_handlers(app)

    # Root health check endpoint
    app.include_router(health.router)
    # Strictly versioned /api/v1 endpoints
    app.include_router(v1_router, prefix=settings.API_V1_PREFIX)

    return app


app = create_app()

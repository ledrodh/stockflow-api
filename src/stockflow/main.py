"""FastAPI application entrypoint for StockFlow API."""

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from stockflow import __version__
from stockflow.api.v1.endpoints import health
from stockflow.api.v1.router import v1_router
from stockflow.core.config import settings
from stockflow.core.exceptions import register_exception_handlers
from stockflow.db.session import AsyncSessionLocal, engine
from stockflow.services.order_service import cleanup_expired_idempotency_keys

logger = logging.getLogger(__name__)


async def _periodic_idempotency_cleanup(interval_seconds: int = 3600) -> None:
    """Periodically purge expired idempotency records in an isolated maintenance session."""
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            async with AsyncSessionLocal() as session:
                purged = await cleanup_expired_idempotency_keys(session)
                if purged > 0:
                    logger.info("Purged %d expired idempotency keys.", purged)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.warning("Idempotency background cleanup encounter error: %s", exc)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup, background maintenance routines, and graceful shutdown."""
    cleanup_task = None
    if settings.APP_ENV != "testing":
        cleanup_task = asyncio.create_task(_periodic_idempotency_cleanup())

    yield

    if cleanup_task is not None:
        cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup_task

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

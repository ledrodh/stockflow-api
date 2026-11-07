"""Health check endpoint verifying real PostgreSQL database connectivity."""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from stockflow import __version__
from stockflow.api.dependencies import DBSessionDep
from stockflow.core.config import settings
from stockflow.schemas.common import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Deep health check testing real PostgreSQL connectivity",
)
async def health_check(session: DBSessionDep) -> HealthResponse | JSONResponse:
    """Execute a live SELECT 1 query against PostgreSQL to verify database readiness."""
    try:
        result: int = int((await session.execute(text("SELECT 1"))).scalar_one())
        if result != 1:
            raise RuntimeError("Unexpected result from database ping.")
        return HealthResponse(
            status="healthy",
            database="connected",
            environment=settings.APP_ENV,
            version=__version__,
        )
    except Exception as exc:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "environment": settings.APP_ENV,
                "version": __version__,
                "detail": f"Database connectivity check failed: {exc}",
            },
        )

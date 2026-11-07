"""Standardized domain exceptions and HTTP exception handlers."""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DBAPIError
from starlette.exceptions import HTTPException as StarletteHTTPException


class StockFlowException(Exception):
    """Base domain exception for StockFlow API."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class AuthenticationError(StockFlowException):
    """Raised when authentication fails (HTTP 401)."""

    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "AUTHENTICATION_FAILED"


class PermissionDeniedError(StockFlowException):
    """Raised when an authenticated user lacks sufficient privileges (HTTP 403)."""

    status_code = status.HTTP_403_FORBIDDEN
    error_code = "PERMISSION_DENIED"


class NotFoundError(StockFlowException):
    """Raised when a requested resource does not exist (HTTP 404)."""

    status_code = status.HTTP_404_NOT_FOUND
    error_code = "RESOURCE_NOT_FOUND"


class ConflictError(StockFlowException):
    """Raised when a request conflicts with current resource state (HTTP 409)."""

    status_code = status.HTTP_409_CONFLICT
    error_code = "RESOURCE_CONFLICT"


class InsufficientStockError(ConflictError):
    """Raised when product stock is insufficient to fulfill an order or movement (HTTP 409)."""

    error_code = "INSUFFICIENT_STOCK"


class IdempotencyConflictError(ConflictError):
    """Raised when an idempotency key is reused with another payload or is in-flight (409)."""

    error_code = "IDEMPOTENCY_CONFLICT"


class DatabaseLockTimeoutError(StockFlowException):
    """Raised when PostgreSQL row lock acquisition times out under contention (HTTP 503)."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "LOCK_TIMEOUT"

    def __init__(
        self,
        message: str = (
            "Database row lock acquisition timed out under concurrent contention. Please retry."
        ),
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)


class DomainValidationError(StockFlowException):
    """Raised when business rule validation fails (HTTP 422)."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "VALIDATION_ERROR"


def build_error_payload(
    error_code: str,
    message: str,
    details: Any = None,
) -> dict[str, Any]:
    """Build a standardized HTTP error response body."""
    return {
        "detail": message,
        "error": {
            "code": error_code,
            "message": message,
            "details": details if details is not None else {},
        },
    }


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers for consistent HTTP error responses."""

    @app.exception_handler(StockFlowException)
    async def stockflow_exception_handler(
        _request: Request, exc: StockFlowException
    ) -> JSONResponse:
        headers: dict[str, str] = {}
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            headers["WWW-Authenticate"] = "Bearer"
        elif exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            headers["Retry-After"] = "1"
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(exc.error_code, exc.message, exc.details),
            headers=headers,
        )

    @app.exception_handler(DBAPIError)
    async def dbapi_exception_handler(_request: Request, exc: DBAPIError) -> JSONResponse:
        orig = getattr(exc, "orig", None)
        pgcode = getattr(orig, "pgcode", None) or getattr(orig, "sqlstate", None)
        error_str = str(exc).lower()
        if pgcode == "55P03" or "55p03" in error_str or "lock_not_available" in error_str:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=build_error_payload(
                    "LOCK_TIMEOUT",
                    "Database row lock acquisition timed out under contention. Please retry.",
                    {"retryable": True},
                ),
                headers={"Retry-After": "1"},
            )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=build_error_payload("DATABASE_ERROR", "A database error occurred."),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        _request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        status_map = {
            status.HTTP_401_UNAUTHORIZED: "AUTHENTICATION_FAILED",
            status.HTTP_403_FORBIDDEN: "PERMISSION_DENIED",
            status.HTTP_404_NOT_FOUND: "RESOURCE_NOT_FOUND",
            status.HTTP_409_CONFLICT: "RESOURCE_CONFLICT",
            status.HTTP_422_UNPROCESSABLE_ENTITY: "VALIDATION_ERROR",
        }
        error_code = status_map.get(exc.status_code, "HTTP_ERROR")
        message = exc.detail if isinstance(exc.detail, str) else "HTTP error occurred."
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error_payload(error_code, message),
            headers=dict(exc.headers) if exc.headers else {},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        sanitized_errors = [
            {
                "loc": list(err.get("loc", [])),
                "msg": err.get("msg", ""),
                "type": err.get("type", ""),
            }
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=build_error_payload(
                "VALIDATION_ERROR",
                "Request payload validation failed.",
                {"errors": sanitized_errors},
            ),
        )

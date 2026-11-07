"""Pydantic schemas package."""

from stockflow.schemas.auth import TokenResponse, UserCreate, UserLogin, UserResponse
from stockflow.schemas.common import HealthResponse, PaginatedResponse
from stockflow.schemas.inventory import InventoryMovementCreate, InventoryMovementResponse
from stockflow.schemas.order import (
    OrderCreate,
    OrderItemCreate,
    OrderItemResponse,
    OrderResponse,
)
from stockflow.schemas.product import ProductCreate, ProductResponse, ProductUpdate

__all__ = [
    "HealthResponse",
    "InventoryMovementCreate",
    "InventoryMovementResponse",
    "OrderCreate",
    "OrderItemCreate",
    "OrderItemResponse",
    "OrderResponse",
    "PaginatedResponse",
    "ProductCreate",
    "ProductResponse",
    "ProductUpdate",
    "TokenResponse",
    "UserCreate",
    "UserLogin",
    "UserResponse",
]

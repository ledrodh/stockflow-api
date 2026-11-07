"""Main API v1 router aggregating all domain endpoint routers."""

from fastapi import APIRouter

from stockflow.api.v1.endpoints import auth, dashboard, health, inventory, orders, products

v1_router = APIRouter()
v1_router.include_router(health.router)
v1_router.include_router(dashboard.router)
v1_router.include_router(auth.router)
v1_router.include_router(products.router)
v1_router.include_router(orders.router)
v1_router.include_router(inventory.router)

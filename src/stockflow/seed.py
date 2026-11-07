"""Seed demo products and an initial admin account for interactive dashboard exploration."""

import asyncio
import os
import sys
from decimal import Decimal

from sqlalchemy import select

from stockflow.core.config import settings
from stockflow.core.security import get_password_hash
from stockflow.db.session import AsyncSessionLocal, engine
from stockflow.models.inventory import InventoryMovement, MovementType
from stockflow.models.product import Product
from stockflow.models.user import User, UserRole

DEFAULT_ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@stockflow.io")
DEFAULT_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "AdminPassword123!")

DEMO_PRODUCTS = [
    {
        "sku": "MACBOOK-M3-MAX",
        "name": 'MacBook Pro 16" M3 Max 36GB',
        "description": "Space Black, 1TB SSD",
        "price": Decimal("24999.00"),
        "stock_quantity": 8,
        "min_stock": 5,
    },
    {
        "sku": "DELL-ULTRA-34",
        "name": 'Dell UltraSharp 34" Curved WQHD Monitor',
        "description": "IPS Black, 90W USB-C Hub",
        "price": Decimal("4899.00"),
        "stock_quantity": 12,
        "min_stock": 5,
    },
    {
        "sku": "KEYB-LOGI-MX",
        "name": "Logitech MX Mechanical Keyboard",
        "description": "Tactile Quiet switches, Bluetooth & Bolt",
        "price": Decimal("799.00"),
        "stock_quantity": 25,
        "min_stock": 10,
    },
    {
        "sku": "MOUSE-MX-MASTER",
        "name": "Logitech MX Master 3S Mouse",
        "description": "Quiet 8K DPI optical sensor",
        "price": Decimal("599.00"),
        "stock_quantity": 3,  # Critical stock (< min_stock 5) to display the warning card
        "min_stock": 5,
    },
    {
        "sku": "SSD-SAMSUNG-990",
        "name": "Samsung 990 Pro 2TB NVMe M.2 SSD",
        "description": "PCIe 4.0 up to 7450 MB/s",
        "price": Decimal("1299.00"),
        "stock_quantity": 15,
        "min_stock": 5,
    },
]


async def seed_demo_data() -> None:
    """Populate database with default admin user and demo catalog products with ledger entries."""
    if settings.APP_ENV == "production" and not settings.ENABLE_DEMO_SEED:
        print(
            "[ERROR] Seeding demo data is blocked in production mode. "
            "Set ENABLE_DEMO_SEED=true and supply explicit ADMIN_EMAIL / ADMIN_PASSWORD "
            "environment variables to proceed.",
            file=sys.stderr,
        )
        sys.exit(1)

    async with AsyncSessionLocal() as session:
        # 1. Admin User
        admin_stmt = select(User).where(User.email == DEFAULT_ADMIN_EMAIL)
        admin = (await session.execute(admin_stmt)).scalar_one_or_none()
        if admin is None:
            admin = User(
                email=DEFAULT_ADMIN_EMAIL,
                hashed_password=get_password_hash(DEFAULT_ADMIN_PASSWORD),
                full_name="StockFlow Admin",
                role=UserRole.ADMIN.value,
                is_active=True,
            )
            session.add(admin)
            await session.flush()
            print(f"[OK] Admin created: {DEFAULT_ADMIN_EMAIL}")

        # 2. Customer User (non-production only)
        if settings.APP_ENV != "production":
            customer_stmt = select(User).where(User.email == "customer@stockflow.io")
            customer = (await session.execute(customer_stmt)).scalar_one_or_none()
            if customer is None:
                customer = User(
                    email="customer@stockflow.io",
                    hashed_password=get_password_hash("CustomerSecret#2026"),
                    full_name="Demo Customer",
                    role=UserRole.CUSTOMER.value,
                    is_active=True,
                )
                session.add(customer)
                await session.flush()
                print("[OK] Demo customer created: customer@stockflow.io")

        # 3. Products + Initial Ledger Movements
        for item in DEMO_PRODUCTS:
            prod_stmt = select(Product).where(Product.sku == item["sku"])
            existing_prod = (await session.execute(prod_stmt)).scalar_one_or_none()
            if existing_prod is None:
                new_prod = Product(
                    sku=item["sku"],
                    name=item["name"],
                    description=item["description"],
                    price=item["price"],
                    stock_quantity=item["stock_quantity"],
                    min_stock=item["min_stock"],
                    is_active=True,
                )
                session.add(new_prod)
                await session.flush()

                movement = InventoryMovement(
                    product_id=new_prod.id,
                    type=MovementType.IN.value,
                    quantity=new_prod.stock_quantity,
                    previous_stock=0,
                    new_stock=new_prod.stock_quantity,
                    reference_id=f"INIT-{new_prod.sku}",
                    reason="Initial catalog stock entry",
                    created_by=admin.id,
                )
                session.add(movement)
                print(f"[OK] Product inserted: {new_prod.sku} ({new_prod.stock_quantity} units)")

        await session.commit()
        print("\n[SUCCESS] Database populated successfully!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_demo_data())

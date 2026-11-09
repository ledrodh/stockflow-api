"""Seed demo products and an initial admin account for interactive dashboard exploration."""

import asyncio
import os
import sys
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from stockflow.core.config import settings
from stockflow.core.security import get_password_hash
from stockflow.db.session import AsyncSessionLocal, engine
from stockflow.models.inventory import InventoryMovement, MovementType
from stockflow.models.order import Order
from stockflow.models.product import Product
from stockflow.models.user import User, UserRole

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
    if settings.APP_ENV == "production":
        if not settings.ENABLE_DEMO_SEED:
            print(
                "[ERROR] Seeding demo data is blocked in production mode. "
                "ENABLE_DEMO_SEED=true is required.",
                file=sys.stderr,
            )
            sys.exit(1)

        admin_email = os.getenv("ADMIN_EMAIL")
        admin_password = os.getenv("ADMIN_PASSWORD")

        if not admin_email or not admin_password:
            print(
                "[ERROR] In production, explicit ADMIN_EMAIL and ADMIN_PASSWORD "
                "environment variables are strictly mandatory.",
                file=sys.stderr,
            )
            sys.exit(1)

        weak_passwords = {"AdminPassword123!", "admin", "password", "12345678", "stockflow"}
        if admin_password in weak_passwords or len(admin_password) < 12:
            print(
                "[ERROR] In production, ADMIN_PASSWORD cannot be a known default or "
                "weaker than 12 characters.",
                file=sys.stderr,
            )
            sys.exit(1)
    else:
        admin_email = os.getenv("ADMIN_EMAIL", "admin@stockflow.io")
        admin_password = os.getenv("ADMIN_PASSWORD", "AdminPassword123!")

    async with AsyncSessionLocal() as session:
        # 1. Admin User
        admin_stmt = select(User).where(User.email == admin_email)
        admin = (await session.execute(admin_stmt)).scalar_one_or_none()
        if admin is None:
            admin = User(
                email=admin_email,
                hashed_password=get_password_hash(admin_password),
                full_name="StockFlow Admin",
                role=UserRole.ADMIN.value,
                is_active=True,
            )
            session.add(admin)
            await session.flush()
            print(f"[OK] Admin created: {admin_email}")

        # 2. Customer User (non-production only)
        customer: User | None = None
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
                    movement_sequence=1,
                    type=MovementType.OPENING.value,
                    quantity=new_prod.stock_quantity,
                    previous_stock=0,
                    new_stock=new_prod.stock_quantity,
                    reference_id=f"INIT-{new_prod.sku}",
                    reason="Initial catalog opening stock",
                    created_by=admin.id,
                )
                session.add(movement)
                print(f"[OK] Product inserted: {new_prod.sku} ({new_prod.stock_quantity} units)")

        await session.commit()

        # 4. Create sample demo orders if none exist
        from stockflow.schemas.order import OrderCreate, OrderItemCreate
        from stockflow.services.order_service import cancel_order_atomic, create_order_atomic

        order_stmt = select(Order)
        existing_orders = (await session.execute(order_stmt)).first()
        if existing_orders is None and customer is not None:
            customer_id = customer.id
            macbook_id = (
                await session.execute(select(Product.id).where(Product.sku == "MACBOOK-M3-MAX"))
            ).scalar_one()
            mouse_id = (
                await session.execute(select(Product.id).where(Product.sku == "MOUSE-MX-MASTER"))
            ).scalar_one()
            payload1 = OrderCreate(
                items=[
                    OrderItemCreate(product_id=macbook_id, quantity=1),
                    OrderItemCreate(product_id=mouse_id, quantity=1),
                ]
            )
            order1 = await create_order_atomic(
                session=session,
                user_id=customer_id,
                payload=payload1,
                idempotency_key=f"demo-seed-order-1-{uuid4()}",
            )
            print(f"[OK] Demo Order 1 created: {order1.id} (R$ {order1.total_amount})")

            dell_id = (
                await session.execute(select(Product.id).where(Product.sku == "DELL-ULTRA-34"))
            ).scalar_one()
            payload2 = OrderCreate(
                items=[
                    OrderItemCreate(product_id=dell_id, quantity=1),
                ]
            )
            order2 = await create_order_atomic(
                session=session,
                user_id=customer_id,
                payload=payload2,
                idempotency_key=f"demo-seed-order-2-{uuid4()}",
            )
            print(f"[OK] Demo Order 2 created: {order2.id} (R$ {order2.total_amount})")

            keyb_id = (
                await session.execute(select(Product.id).where(Product.sku == "KEYB-LOGI-MX"))
            ).scalar_one()
            payload3 = OrderCreate(
                items=[
                    OrderItemCreate(product_id=keyb_id, quantity=2),
                ]
            )
            order3 = await create_order_atomic(
                session=session,
                user_id=customer_id,
                payload=payload3,
                idempotency_key=f"demo-seed-order-3-{uuid4()}",
            )
            await cancel_order_atomic(
                session=session,
                order_id=order3.id,
                user_id=customer_id,
                is_admin=False,
            )
            print(f"[OK] Demo Order 3 created & cancelled (restocked): {order3.id}")

        print("\n[SUCCESS] Database populated successfully!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_demo_data())

"""Initial database schema with constraints, idempotency, and immutable ledger.

Revision ID: 20261106_0001
Revises:
Create Date: 2026-11-06 21:50:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20261106_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create core tables, constraints, indexes, and immutability trigger."""
    # 1. Users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.String(length=32),
            server_default="customer",
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default="true",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('admin', 'customer')",
            name=op.f("ck_users_valid_user_role"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # 2. Products table
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "stock_quantity",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default="true",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "price >= 0",
            name=op.f("ck_products_price_non_negative"),
        ),
        sa.CheckConstraint(
            "stock_quantity >= 0",
            name=op.f("ck_products_stock_quantity_non_negative"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_products")),
    )
    op.create_index(op.f("ix_products_sku"), "products", ["sku"], unique=True)
    op.create_index(op.f("ix_products_name"), "products", ["name"], unique=False)
    op.create_index(op.f("ix_products_is_active"), "products", ["is_active"], unique=False)

    # 3. Orders table
    op.create_table(
        "orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="CONFIRMED",
            nullable=False,
        ),
        sa.Column("total_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('PENDING', 'CONFIRMED', 'CANCELLED')",
            name=op.f("ck_orders_valid_order_status"),
        ),
        sa.CheckConstraint(
            "total_amount >= 0",
            name=op.f("ck_orders_total_amount_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_orders_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_orders")),
    )
    op.create_index(op.f("ix_orders_user_id"), "orders", ["user_id"], unique=False)

    # 4. OrderItems table
    op.create_table(
        "order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_name_snapshot", sa.String(length=255), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("subtotal", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.CheckConstraint(
            "unit_price >= 0",
            name=op.f("ck_order_items_unit_price_non_negative"),
        ),
        sa.CheckConstraint(
            "quantity > 0",
            name=op.f("ck_order_items_quantity_positive"),
        ),
        sa.CheckConstraint(
            "subtotal >= 0",
            name=op.f("ck_order_items_subtotal_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
            name=op.f("fk_order_items_order_id_orders"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_order_items_product_id_products"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_order_items")),
    )
    op.create_index(op.f("ix_order_items_order_id"), "order_items", ["order_id"], unique=False)
    op.create_index(op.f("ix_order_items_product_id"), "order_items", ["product_id"], unique=False)

    # 5. InventoryMovements table (immutable ledger)
    op.create_table(
        "inventory_movements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("previous_stock", sa.Integer(), nullable=False),
        sa.Column("new_stock", sa.Integer(), nullable=False),
        sa.Column("reference_id", sa.String(length=128), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "type IN ('IN', 'OUT', 'ADJUSTMENT', 'RETURN')",
            name=op.f("ck_inventory_movements_valid_movement_type"),
        ),
        sa.CheckConstraint(
            "quantity > 0",
            name=op.f("ck_inventory_movements_movement_quantity_positive"),
        ),
        sa.CheckConstraint(
            "previous_stock >= 0",
            name=op.f("ck_inventory_movements_previous_stock_non_negative"),
        ),
        sa.CheckConstraint(
            "new_stock >= 0",
            name=op.f("ck_inventory_movements_new_stock_non_negative"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name=op.f("fk_inventory_movements_created_by_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_inventory_movements_product_id_products"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_inventory_movements")),
    )
    op.create_index(
        op.f("ix_inventory_movements_product_id"),
        "inventory_movements",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_inventory_movements_type"),
        "inventory_movements",
        ["type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_inventory_movements_reference_id"),
        "inventory_movements",
        ["reference_id"],
        unique=False,
    )

    # PostgreSQL trigger enforcing append-only immutability on inventory_movements
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_inventory_movement_mutation()
        RETURNS TRIGGER AS $$
        BEGIN
            RAISE EXCEPTION 'inventory_movements table is append-only and immutable.';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_immutable_inventory_movements
        BEFORE UPDATE OR DELETE ON inventory_movements
        FOR EACH ROW EXECUTE FUNCTION prevent_inventory_movement_mutation();
        """
    )

    # 6. IdempotencyKeys table
    op.create_table(
        "idempotency_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="PROCESSING",
            nullable=False,
        ),
        sa.Column("response_code", sa.Integer(), nullable=True),
        sa.Column("response_body", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('PROCESSING', 'COMPLETED', 'FAILED')",
            name=op.f("ck_idempotency_keys_valid_idempotency_status"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_idempotency_keys_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_idempotency_keys")),
        sa.UniqueConstraint("user_id", "key", name="uq_idempotency_user_key"),
    )
    op.create_index(
        op.f("ix_idempotency_keys_user_id"),
        "idempotency_keys",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop all tables and triggers in reverse dependency order."""
    op.drop_index(op.f("ix_idempotency_keys_user_id"), table_name="idempotency_keys")
    op.drop_table("idempotency_keys")

    op.execute("DROP TRIGGER IF EXISTS trg_immutable_inventory_movements ON inventory_movements;")
    op.execute("DROP FUNCTION IF EXISTS prevent_inventory_movement_mutation();")

    op.drop_index(op.f("ix_inventory_movements_reference_id"), table_name="inventory_movements")
    op.drop_index(op.f("ix_inventory_movements_type"), table_name="inventory_movements")
    op.drop_index(op.f("ix_inventory_movements_product_id"), table_name="inventory_movements")
    op.drop_table("inventory_movements")

    op.drop_index(op.f("ix_order_items_product_id"), table_name="order_items")
    op.drop_index(op.f("ix_order_items_order_id"), table_name="order_items")
    op.drop_table("order_items")

    op.drop_index(op.f("ix_orders_user_id"), table_name="orders")
    op.drop_table("orders")

    op.drop_index(op.f("ix_products_is_active"), table_name="products")
    op.drop_index(op.f("ix_products_name"), table_name="products")
    op.drop_index(op.f("ix_products_sku"), table_name="products")
    op.drop_table("products")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

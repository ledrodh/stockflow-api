"""Add movement_sequence, adjustment_direction, OPENING type, and arithmetic constraints.

Revision ID: 20261107_0003
Revises: 20261107_0002
Create Date: 2026-11-07 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261107_0003"
down_revision: str | None = "20261107_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add index on idempotency_keys(expires_at)
    op.create_index(
        op.f("ix_idempotency_keys_expires_at"),
        "idempotency_keys",
        ["expires_at"],
        unique=False,
    )

    # 2. Add columns movement_sequence and adjustment_direction to inventory_movements
    op.add_column(
        "inventory_movements",
        sa.Column("movement_sequence", sa.Integer(), nullable=True),
    )
    op.add_column(
        "inventory_movements",
        sa.Column("adjustment_direction", sa.String(length=16), nullable=True),
    )

    # 3. Disable immutable trigger during backfill
    op.execute("ALTER TABLE inventory_movements DISABLE TRIGGER trg_immutable_inventory_movements;")

    # 4. Backfill OPENING movements for products that have stock > 0 but no existing movements
    op.execute(
        """
        INSERT INTO inventory_movements (
            id, product_id, type, quantity, previous_stock, new_stock,
            movement_sequence, reference_id, reason, created_at
        )
        SELECT
            gen_random_uuid(), p.id, 'OPENING', p.stock_quantity, 0, p.stock_quantity,
            1, 'INIT-' || p.sku, 'Initial catalog opening stock', p.created_at
        FROM products p
        WHERE NOT EXISTS (
            SELECT 1 FROM inventory_movements m WHERE m.product_id = p.id
        )
        AND p.stock_quantity > 0;
        """
    )

    # 5. Backfill movement_sequence using ROW_NUMBER() per product
    op.execute(
        """
        WITH numbered AS (
            SELECT id, ROW_NUMBER() OVER (
                PARTITION BY product_id ORDER BY created_at ASC, id ASC
            ) as seq
            FROM inventory_movements
        )
        UPDATE inventory_movements m
        SET movement_sequence = numbered.seq
        FROM numbered
        WHERE m.id = numbered.id AND m.movement_sequence IS NULL;
        """
    )

    # 6. Re-enable immutable trigger
    op.execute("ALTER TABLE inventory_movements ENABLE TRIGGER trg_immutable_inventory_movements;")

    # 7. Alter movement_sequence to NOT NULL
    op.alter_column(
        "inventory_movements",
        "movement_sequence",
        existing_type=sa.Integer(),
        nullable=False,
    )

    # 8. Update check constraint on movement types to include 'OPENING'
    op.drop_constraint(
        op.f("ck_inventory_movements_valid_movement_type"),
        "inventory_movements",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_inventory_movements_valid_movement_type"),
        "inventory_movements",
        "type IN ('IN', 'OUT', 'ADJUSTMENT', 'RETURN', 'OPENING')",
    )

    # 9. Add check constraint for movement_sequence >= 1
    op.create_check_constraint(
        op.f("ck_inventory_movements_movement_sequence_positive"),
        "inventory_movements",
        "movement_sequence >= 1",
    )

    # 10. Add unique constraint on (product_id, movement_sequence)
    op.create_unique_constraint(
        op.f("uq_inventory_movements_product_sequence"),
        "inventory_movements",
        ["product_id", "movement_sequence"],
    )

    # 11. Add check constraint on adjustment_direction
    op.create_check_constraint(
        op.f("chk_inventory_movement_adjustment_direction"),
        "inventory_movements",
        "(type != 'ADJUSTMENT' AND adjustment_direction IS NULL) OR "
        "(type = 'ADJUSTMENT' AND adjustment_direction IN ('INCREASE', 'DECREASE'))",
    )

    # 12. Add check constraint for ledger arithmetic consistency
    op.create_check_constraint(
        op.f("chk_inventory_movement_arithmetic"),
        "inventory_movements",
        """
        (
            (type IN ('IN', 'RETURN', 'OPENING') AND new_stock = previous_stock + quantity
             AND adjustment_direction IS NULL) OR
            (type = 'OUT' AND new_stock = previous_stock - quantity
             AND adjustment_direction IS NULL) OR
            (type = 'ADJUSTMENT' AND adjustment_direction = 'INCREASE'
             AND new_stock = previous_stock + quantity) OR
            (type = 'ADJUSTMENT' AND adjustment_direction = 'DECREASE'
             AND new_stock = previous_stock - quantity)
        )
        """,
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("chk_inventory_movement_arithmetic"),
        "inventory_movements",
        type_="check",
    )
    op.drop_constraint(
        op.f("chk_inventory_movement_adjustment_direction"),
        "inventory_movements",
        type_="check",
    )
    op.drop_constraint(
        op.f("uq_inventory_movements_product_sequence"),
        "inventory_movements",
        type_="unique",
    )
    op.drop_constraint(
        op.f("ck_inventory_movements_movement_sequence_positive"),
        "inventory_movements",
        type_="check",
    )

    op.drop_constraint(
        op.f("ck_inventory_movements_valid_movement_type"),
        "inventory_movements",
        type_="check",
    )
    op.create_check_constraint(
        op.f("ck_inventory_movements_valid_movement_type"),
        "inventory_movements",
        "type IN ('IN', 'OUT', 'ADJUSTMENT', 'RETURN')",
    )

    op.drop_column("inventory_movements", "adjustment_direction")
    op.drop_column("inventory_movements", "movement_sequence")

    op.drop_index(op.f("ix_idempotency_keys_expires_at"), table_name="idempotency_keys")

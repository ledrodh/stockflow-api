"""Add min_stock column and constraint to products.

Revision ID: 20261107_0002
Revises: 20261106_0001
Create Date: 2026-11-07 00:15:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261107_0002"
down_revision: str | None = "20261106_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add min_stock column to products table with non-negative check constraint."""
    op.add_column(
        "products",
        sa.Column("min_stock", sa.Integer(), server_default="5", nullable=False),
    )
    op.create_check_constraint(
        op.f("ck_products_min_stock_non_negative"),
        "products",
        "min_stock >= 0",
    )


def downgrade() -> None:
    """Drop min_stock column and check constraint."""
    op.drop_constraint(
        op.f("ck_products_min_stock_non_negative"),
        "products",
        type_="check",
    )
    op.drop_column("products", "min_stock")

"""Snapshot-consistent Stock Reconciliation Engine verifying ledger integrity."""

from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from stockflow.models.inventory import AdjustmentDirection, InventoryMovement, MovementType
from stockflow.models.product import Product
from stockflow.schemas.reconciliation import ProductDiscrepancy, StockReconciliationReport


async def run_inventory_reconciliation(
    session: AsyncSession,
) -> StockReconciliationReport:
    """Execute a comprehensive, snapshot-consistent stock reconciliation.

    Verifies in a REPEATABLE READ, READ ONLY transaction:
      1. Sequence Continuity: movement_sequence forms an unbroken 1..N range per product.
      2. Chain Continuity: movement[k].previous_stock == movement[k-1].new_stock.
      3. Arithmetic Integrity: product.stock_quantity == sum of all signed ledger movements.
    """
    if session.in_transaction():
        await session.commit()

    async with session.begin():
        await session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;"))

        prod_stmt = select(Product).order_by(Product.sku.asc())
        products = (await session.execute(prod_stmt)).scalars().all()

        mov_stmt = select(InventoryMovement).order_by(
            InventoryMovement.product_id.asc(),
            InventoryMovement.movement_sequence.asc(),
        )
        movements = (await session.execute(mov_stmt)).scalars().all()

        movements_by_product: dict[UUID, list[InventoryMovement]] = defaultdict(list)
        for m in movements:
            movements_by_product[m.product_id].append(m)

        discrepancies: list[ProductDiscrepancy] = []
        consistent_count = 0

        for product in products:
            prod_movements = movements_by_product.get(product.id, [])
            seq_errors: list[str] = []
            continuity_errors: list[str] = []
            arithmetic_errors: list[str] = []

            running_ledger_stock = 0

            if not prod_movements:
                if product.stock_quantity != 0:
                    arithmetic_errors.append(
                        f"Product has stock_quantity={product.stock_quantity} "
                        "but zero ledger movements recorded."
                    )
            else:
                expected_sequence = 1
                last_new_stock = 0

                for idx, mov in enumerate(prod_movements):
                    # 1. Sequence Continuity Check
                    if mov.movement_sequence != expected_sequence:
                        seq_errors.append(
                            f"Expected sequence {expected_sequence} but found "
                            f"sequence {mov.movement_sequence} (movement {mov.id})."
                        )
                    expected_sequence += 1

                    # 2. Chain Continuity Check
                    if idx == 0:
                        if mov.previous_stock != 0:
                            continuity_errors.append(
                                f"Initial movement sequence {mov.movement_sequence} "
                                f"previous_stock must be 0, found {mov.previous_stock}."
                            )
                    else:
                        if mov.previous_stock != last_new_stock:
                            continuity_errors.append(
                                f"Movement sequence {mov.movement_sequence} previous_stock "
                                f"({mov.previous_stock}) does not match prior "
                                f"new_stock ({last_new_stock})."
                            )

                    # 3. Arithmetic Integrity Check
                    if mov.type in (
                        MovementType.IN.value,
                        MovementType.RETURN.value,
                        MovementType.OPENING.value,
                    ):
                        running_ledger_stock += mov.quantity
                        expected_new = mov.previous_stock + mov.quantity
                    elif mov.type == MovementType.OUT.value:
                        running_ledger_stock -= mov.quantity
                        expected_new = mov.previous_stock - mov.quantity
                    elif mov.type == MovementType.ADJUSTMENT.value:
                        if mov.adjustment_direction == AdjustmentDirection.INCREASE.value:
                            running_ledger_stock += mov.quantity
                            expected_new = mov.previous_stock + mov.quantity
                        elif mov.adjustment_direction == AdjustmentDirection.DECREASE.value:
                            running_ledger_stock -= mov.quantity
                            expected_new = mov.previous_stock - mov.quantity
                        else:
                            arithmetic_errors.append(
                                f"Movement seq {mov.movement_sequence} is ADJUSTMENT with unknown "
                                f"direction '{mov.adjustment_direction}'."
                            )
                            expected_new = mov.new_stock
                    else:
                        arithmetic_errors.append(
                            f"Movement seq {mov.movement_sequence} has unknown type '{mov.type}'."
                        )
                        expected_new = mov.new_stock

                    if mov.new_stock != expected_new:
                        arithmetic_errors.append(
                            f"Movement seq {mov.movement_sequence} new_stock ({mov.new_stock}) != "
                            f"expected ({expected_new})."
                        )

                    last_new_stock = mov.new_stock

                if running_ledger_stock != product.stock_quantity:
                    arithmetic_errors.append(
                        f"Product stock_quantity ({product.stock_quantity}) does not match "
                        f"calculated ledger stock ({running_ledger_stock})."
                    )

            is_item_consistent = not (seq_errors or continuity_errors or arithmetic_errors)
            if is_item_consistent:
                consistent_count += 1
            else:
                discrepancies.append(
                    ProductDiscrepancy(
                        product_id=product.id,
                        sku=product.sku,
                        product_name=product.name,
                        current_stock_quantity=product.stock_quantity,
                        calculated_ledger_stock=running_ledger_stock,
                        discrepancy_delta=product.stock_quantity - running_ledger_stock,
                        sequence_errors=seq_errors,
                        continuity_errors=continuity_errors,
                        arithmetic_errors=arithmetic_errors,
                        is_consistent=False,
                    )
                )

        report = StockReconciliationReport(
            generated_at=datetime.now(UTC),
            snapshot_isolation_level="REPEATABLE READ, READ ONLY",
            total_products_checked=len(products),
            consistent_products_count=consistent_count,
            discrepant_products_count=len(discrepancies),
            is_consistent=len(discrepancies) == 0,
            discrepancies=discrepancies,
        )

    return report

"""CLI entrypoint for running stock reconciliation directly against PostgreSQL."""

import asyncio
import sys

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from stockflow.core.config import settings
from stockflow.services.reconciliation_service import run_inventory_reconciliation


async def main() -> int:
    """Execute reconciliation CLI and return exit code 0 on clean, 1 on discrepancies."""
    print("=" * 70)
    print(" STOCKFLOW - Snapshot-Consistent Inventory Ledger Reconciliation")
    print("=" * 70)
    print(
        f"Connecting to: {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )

    engine = create_async_engine(settings.async_database_url, echo=False)
    try:
        async with AsyncSession(engine) as session:
            report = await run_inventory_reconciliation(session)

        print(f"Report Generated At: {report.generated_at.isoformat()}")
        print(f"Isolation Level:     {report.snapshot_isolation_level}")
        print(f"Products Checked:    {report.total_products_checked}")
        print(f"Consistent Count:    {report.consistent_products_count}")
        print(f"Discrepancies Count: {report.discrepant_products_count}")
        print("-" * 70)

        if report.is_consistent:
            print("STATUS: ALL PRODUCTS 100% RECONCILED AND CONSISTENT [OK]")
            print("=" * 70)
            return 0

        print("STATUS: DISCREPANCIES DETECTED [FAILED]")
        for d in report.discrepancies:
            print(f"\n[!] SKU: {d.sku} | Name: {d.product_name}")
            print(f"    Current stock_quantity:   {d.current_stock_quantity}")
            print(f"    Calculated ledger stock:  {d.calculated_ledger_stock}")
            print(f"    Delta (stock - ledger):   {d.discrepancy_delta}")
            if d.sequence_errors:
                print("    Sequence Errors:")
                for err in d.sequence_errors:
                    print(f"      - {err}")
            if d.continuity_errors:
                print("    Continuity Errors:")
                for err in d.continuity_errors:
                    print(f"      - {err}")
            if d.arithmetic_errors:
                print("    Arithmetic Errors:")
                for err in d.arithmetic_errors:
                    print(f"      - {err}")
        print("=" * 70)
        return 1
    finally:
        await engine.dispose()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

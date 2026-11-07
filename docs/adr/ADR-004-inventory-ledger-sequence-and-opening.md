# ADR-004: Inventory Ledger Movement Sequencing and Opening Stock Invariant

## Status
Accepted

## Context
While the StockFlow inventory system implemented append-only immutability via database triggers (`trg_immutable_inventory_movements`), movements previously lacked a strictly enforced per-product sequence numbering and a formal `OPENING` entry for initial catalog stock.

Without per-product sequential numbering:
1. Concurrently inserted movements or movements recorded with identical millisecond timestamps could not be deterministically ordered.
2. Gap detection (identifying whether a transaction was missed or skipped) was impossible.
3. Establishing chain continuity ($previous\_stock_N == new\_stock_{N-1}$) was vulnerable to ambiguous ordering.
4. When a product was created with positive stock, no explicit opening audit event was recorded, obscuring the origin of initial stock.

## Decision
1. **Explicit Movement Type `OPENING`**:
   - Added `MovementType.OPENING = "OPENING"`.
   - Creating any product with initial stock $> 0$ generates a movement with sequence 1, `previous_stock = 0`, `new_stock = stock_quantity`, `quantity = stock_quantity`.
2. **Deterministic Sequence Numbering (`movement_sequence`)**:
   - Added `movement_sequence: int` with `UniqueConstraint("product_id", "movement_sequence")`.
   - Sequence generation executes under row-level `SELECT FOR UPDATE` on the parent product row, calculating `COALESCE(MAX(movement_sequence), 0) + 1` atomically.
   - Enforced by database check constraint: `movement_sequence >= 1`.
3. **Explicit Adjustment Direction (`adjustment_direction`)**:
   - Manual audit adjustments require an explicit direction: `INCREASE` or `DECREASE`.
   - Database constraint ensures `adjustment_direction` is non-null for `ADJUSTMENT` and null for all other movement types.
4. **Database-Level Arithmetic Check Constraint**:
   - PostgreSQL `chk_inventory_movement_arithmetic` validates at the database level that:
     $$new\_stock = previous\_stock \pm quantity$$
     according to the movement type and direction, rejecting inconsistent transactions before commit.

## Consequences
- **Positive**: Complete deterministic ordering of ledger transitions; instant detection of missing or duplicate sequence numbers; mathematically enforced arithmetic balance.
- **Negative**: Requires querying the maximum sequence under product row lock prior to movement insertion (mitigated by existing `SELECT FOR UPDATE` design which serializes mutations).

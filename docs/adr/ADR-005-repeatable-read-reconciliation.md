# ADR-005: Snapshot-Consistent Inventory Reconciliation Engine

## Status
Accepted

## Context
In transactional e-commerce and warehouse inventory management, discrepancies may emerge if application bugs, unhandled rollbacks, or out-of-band database operations desynchronize current physical balances (`products.stock_quantity`) from the immutable ledger (`inventory_movements`).

Validating consistency across large catalogs while live concurrent orders are processing creates two risks:
1. **Phantom reads / Non-repeatable reads**: Under `READ COMMITTED` isolation, reading product stock at time $t_0$ and querying corresponding movements at time $t_1$ can capture in-flight transactions committed between queries, generating false discrepancy alarms.
2. **Missing holistic validation**: Simply comparing sums does not detect broken transition chains ($previous\_stock_N \neq new\_stock_{N-1}$) or missing sequential entries.

## Decision
Implement a dedicated **Stock Reconciliation Engine** executing under PostgreSQL `REPEATABLE READ, READ ONLY` transaction isolation:

1. **Snapshot Consistency**:
   - The reconciliation session begins with `SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;`.
   - All catalog products and their corresponding movement ledgers are evaluated against the exact same transactional snapshot in PostgreSQL MVCC, completely immune to concurrent writes or phantom reads.
2. **Three-Tier Verification**:
   - **Tier 1 (Sequence Continuity)**: Validates that `movement_sequence` forms an unbroken, ascending sequence $1, 2, \dots, N$ per product without gaps.
   - **Tier 2 (Chain Continuity)**: Validates that initial movement starts with `previous_stock = 0` and every subsequent movement $k$ has $previous\_stock_k == new\_stock_{k-1}$.
   - **Tier 3 (Arithmetic Sum)**: Validates that $product.stock\_quantity == \sum \text{signed\_ledger\_movements}$.
3. **Dual Execution Interfaces**:
   - REST API: `GET /api/v1/inventory/reconcile` (restricted to system administrators).
   - Administrative CLI: `python -m stockflow.reconcile` exiting with code 0 on clean state and code 1 when discrepancies are detected.

## Consequences
- **Positive**: False alarms from concurrent transactions are eliminated; full diagnostic details on sequence, chain, and arithmetic discrepancies; auditable via CLI and dashboard.
- **Negative**: Long-running `REPEATABLE READ` transactions retain PostgreSQL snapshot references in memory; keeping the reconciliation logic vectorized and read-only minimizes snapshot duration.

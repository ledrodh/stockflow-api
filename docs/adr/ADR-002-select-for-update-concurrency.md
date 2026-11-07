# ADR-002: Pessimistic Concurrency Control with `SELECT FOR UPDATE` and Deterministic Ordering

- **Status:** Accepted
- **Date:** 2026-11-06
- **Context:** Preventing Overselling (Negative Stock) and Deadlocks Under Concurrent Checkout Load

---

## Context and Problem Statement

Under high contention (flash sales, limited-quantity drops), dozens of requests compete simultaneously to purchase the same inventory items.

When applications rely on naive Read-Modify-Write flows under PostgreSQL's default `READ COMMITTED` isolation level without explicit locking:
1. Transaction A reads `stock_quantity = 1`.
2. Transaction B reads `stock_quantity = 1` before Transaction A commits.
3. Both validate `if stock_quantity >= 1` in application code and commit, resulting in **Overselling** (negative inventory in warehouse systems).

Furthermore, when transactions involve multiple products (e.g. Order 1 purchases `[Product A, Product B]` while Order 2 purchases `[Product B, Product A]`), locking rows in client-provided sequence causes circular **deadlocks** inside the database engine.

---

## Decision

We adopted **pessimistic row-level locking (`SELECT ... FOR UPDATE`)** via SQLAlchemy 2.0 coupled with three critical defense layers:

### 1. Canonical Ordering by Primary Key (`ORDER BY products.id ASC`)
Prior to acquiring exclusive row locks, all target product rows are fetched and sorted deterministically:

```python
products_stmt = (
    select(Product)
    .where(Product.id.in_(product_ids))
    .order_by(Product.id.asc())
    .with_for_update()
)
```
Regardless of the item sequence sent by the client, every concurrent transaction requests row locks in the exact same ascending `UUID` sequence, mathematically eliminating circular deadlocks due to out-of-order locking.

### 2. Transaction Lock Timeout (`SET LOCAL lock_timeout`)
We configure `SET LOCAL lock_timeout = '5000ms'` within the transaction. If row acquisition exceeds acceptable thresholds, the transaction fails fast rather than exhausting the database connection pool.

### 3. Defense-in-Depth via Database Check Constraint (`CHECK (stock_quantity >= 0)`)
Beyond application-level validations, the `products` table defines a native check constraint `ck_products_stock_quantity_non_negative` (`stock_quantity >= 0`) at the PostgreSQL DDL level.

---

## Consequences

### Positive
- **Provably Zero Overselling:** Verified by automated stress tests (`tests/integration/test_concurrency.py`), where 10 concurrent requests (`asyncio.gather`) compete for 5 items — exactly 5 succeed with `201 Created`, 5 fail with `409 Conflict`, and the final stock settles exactly at `0`.
- **Deadlock Immunity on Multi-Item Carts:** Deterministic ordering prevents cyclical waiting conditions.
- **Superior User Experience Compared to Optimistic Locking:** Unlike optimistic locking (which aborts competing transactions forcing customers to retry checkouts even when inventory remains), `SELECT FOR UPDATE` queues transactions in microseconds while inventory is available.

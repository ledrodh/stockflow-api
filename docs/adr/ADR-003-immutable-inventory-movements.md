# ADR-003: Append-Only Immutable Inventory Ledger (`InventoryMovement`) and Historical Snapshots

- **Status:** Accepted
- **Date:** 2026-11-06
- **Context:** Traceability, Inventory Auditing, and Order Historical Integrity

---

## Context and Problem Statement

In standard CRUD applications, stock adjustments are often executed purely via `UPDATE products SET stock_quantity = stock_quantity - 1`. This destructive mutation introduces severe operational and accounting deficiencies:

1. **Lack of Explainability:** When a physical warehouse count diverges from the database, it is impossible to determine when, why, or by whom (sale, damage, supplier restock, return) the balance changed.
2. **Historical Data Corruption:** If a catalog product is updated (price increase, name change) or deleted (`DELETE`), past historical orders lose integrity or display inaccurate invoice figures retroactively.

---

## Decision

We implemented three core architectural pillars inspired by **accounting ledgers (*Append-Only Ledger*)**:

### 1. Immutable `inventory_movements` Ledger Table
Every modification to `products.stock_quantity` — including initial catalog seeding, purchase orders (`OUT`), supplier restocks (`IN`), adjustments (`ADJUSTMENT`), and returns (`RETURN`) — appends an immutable entry to `inventory_movements`:
- `product_id`, `type`, `quantity` (`> 0`)
- `previous_stock` and `new_stock` (exact before/after state)
- `reference_id` (e.g. order ID or document reference) and `reason`
- `created_by` and `created_at`

Immutability is enforced across **two distinct layers**:
- **ORM Layer (SQLAlchemy):** Event listeners on `before_update` and `before_delete` block mutation in application memory.
- **RDBMS Layer (PostgreSQL Trigger):** The trigger `trg_immutable_inventory_movements` raises a native database exception if any raw `UPDATE` or `DELETE` SQL statement targets `inventory_movements`.

### 2. Purchase Snapshots in `order_items` (`unit_price` and `product_name_snapshot`)
When an order is placed, `OrderItem` copies the exact active `unit_price` and `name` snapshot. Subsequent product price changes or renames never distort past order records.

### 3. Logical Deletion (*Soft Delete*) for Products
The `DELETE /api/v1/products/{id}` endpoint sets `is_active = False` rather than executing a destructive SQL `DELETE`. This preserves foreign key integrity on historical orders and inventory movements (`RESTRICT`).

---

## Consequences

### Positive
- **100% Audit Traceability:** Every unit count in `products.stock_quantity` can be mathematically reconstructed by replaying the sequential ledger chain `previous_stock -> new_stock`.
- **Financial and Regulatory Compliance:** Past orders remain invariant even after catalog updates or product retirements.

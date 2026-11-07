# ADR-001: PostgreSQL as Single Source of Truth for Transactional Idempotency

- **Status:** Accepted
- **Date:** 2026-11-06
- **Context:** Sales & Inventory Order Engine (`POST /api/v1/orders`)

---

## Context and Problem Statement

In distributed systems, e-commerce platforms, and payment APIs, network transients (client timeouts, mobile disconnects, automated gateway retries) frequently trigger duplicate order submissions. Without robust idempotency guarantees, customers risk double billing and inventory risks overselling.

A common naive approach stores idempotency keys (`Idempotency-Key`) exclusively in **Redis**. However, using two disconnected storage engines (Redis + PostgreSQL) without a two-phase commit (2PC) protocol introduces severe **consistency bugs (Dual-Write Problem)**:

1. If the application commits to PostgreSQL and crashes *before* setting the key in Redis (e.g. process termination or network partition), subsequent client retries will miss the Redis cache and **duplicate the order**.
2. If the application writes to Redis *before* committing to PostgreSQL and the database transaction subsequently rolls back, the client receives a false positive confirmation for an order that does not exist in the database.

---

## Decision

We decided to keep the **authoritative source of truth for idempotency directly inside PostgreSQL** using the dedicated `idempotency_keys` table, constrained by `UNIQUE (user_id, key)`.

The lifecycle of the idempotency record executes **inside the exact same ACID transaction** (`async with session.begin():`) that acquires row locks (`SELECT ... FOR UPDATE`), creates the order and items (`orders`, `order_items`), and logs immutable inventory movements (`inventory_movements`).

### Anatomical Structure of the Idempotency Record

- `user_id` + `key`: Scoped per user account (`uq_idempotency_user_key`), preventing key collisions across different users.
- `request_hash`: Canonical `SHA-256` digest of the normalized order payload. Reusing the same key with differing items or quantities immediately fails with **`409 Conflict` (`IDEMPOTENCY_CONFLICT`)**.
- `status`: Execution state (`PROCESSING`, `COMPLETED`, `FAILED`).
- `response_code` and `response_body` (`JSONB`): Full serialized snapshot of the original `OrderResponse`.

---

## Consequences

### Positive
- **Guaranteed ACID Atomicity:** Either the order, the stock deduction, the inventory ledger, and the idempotency record commit together, or **none of them do (`ROLLBACK`)**.
- **Resilient, Lean Infrastructure:** Eliminates state drift between an in-memory cache and a relational database.
- **Race Condition Immunity:** The PostgreSQL composite unique constraint (`uq_idempotency_user_key`) natively serializes concurrent duplicate requests arriving in the same millisecond.

### Negative / Trade-offs
- **PostgreSQL I/O Overhead:** Every idempotent request performs a database write. To manage long-term table bloat, the model includes an `expires_at` column, enabling periodic cleanup jobs (`DELETE FROM idempotency_keys WHERE expires_at < NOW()`). If necessary under extreme scale, Redis can serve as a read-through cache layer in front of PostgreSQL, while PostgreSQL remains the transactional source of truth.

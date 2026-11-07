# StockFlow API — High-Integrity Inventory & Order Engine

![Python](https://img.shields.io/badge/Python-3.12%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0_Async-red)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-336791)
![Ruff](https://img.shields.io/badge/Code_Style-Ruff-black)
![Mypy](https://img.shields.io/badge/Type_Check-Mypy_Strict-blue)
![React](https://img.shields.io/badge/Frontend-React_18_%2B_Vite-61dafb)
![Tailwind](https://img.shields.io/badge/Styling-Tailwind_CSS-38bdf8)

**StockFlow API** is a high-integrity inventory and order management engine engineered to **guarantee absolute data consistency under heavy stress and real-world database contention**. Moving beyond simple CRUD patterns, StockFlow implements ACID atomic transactions, pessimistic concurrency control with deadlock prevention (`SELECT ... FOR UPDATE`), database-backed persistent idempotency, and an immutable double-entry inventory ledger (*Append-Only Ledger*).

---

## 🎯 Engineering Highlights

1. **Database-Level Concurrency Control (`SELECT ... FOR UPDATE`):**
   - High-contention purchase requests competing for the remaining units of a product are serialized at the PostgreSQL row level.
   - Products within multi-item orders are sorted deterministically by primary key (`ORDER BY products.id ASC`) prior to lock acquisition, **mathematically eliminating circular deadlocks** caused by concurrent carts locking items in opposite orders.
2. **Transactional PostgreSQL Idempotency (`UNIQUE(user_id, key)`):**
   - The `Idempotency-Key` is persisted and validated within the **exact same ACID transaction** that deducts stock and creates orders, avoiding the *Dual-Write Problem* common to Redis-only architectures.
   - Deterministic `SHA-256` payload hashing: repeating the same key returns the existing order (`201 Created`) without secondary debits; altering the payload while reusing the key triggers an immediate `409 Conflict` (`IDEMPOTENCY_CONFLICT`).
3. **Immutable Inventory Ledger (`InventoryMovement`):**
   - Every stock alteration appends an immutable entry capturing `previous_stock`, `new_stock`, `type` (`IN`, `OUT`, `RETURN`, `ADJUSTMENT`), `reference_id`, and `reason`.
   - Hardened across two layers: SQLAlchemy ORM event listeners and a **native PostgreSQL trigger** (`trg_immutable_inventory_movements`) blocking raw `UPDATE` and `DELETE` queries.
4. **Historical Snapshots & Soft Deletion:**
   - `OrderItem` preserves frozen `unit_price` and `product_name_snapshot` values at the time of purchase.
   - Products are never physically deleted (`is_active = False`), safeguarding relational foreign key integrity across historical transactions.
5. **Modern Security & Role-Based Access Control (RBAC):**
   - Password hashing with **Argon2id** via `pwdlib[argon2]`.
   - Short-lived signed JWT access tokens with strict role separation (`admin` vs `customer`) and forbidden privilege escalation (`extra="forbid"` on public schemas).

---

## 📐 Architecture & Diagrams

### 1. Entity-Relationship Diagram (ERD)

```mermaid
erDiagram
    USERS ||--o{ ORDERS : "places"
    USERS ||--o{ IDEMPOTENCY_KEYS : "owns"
    USERS ||--o{ INVENTORY_MOVEMENTS : "executes"
    PRODUCTS ||--o{ ORDER_ITEMS : "referenced_in"
    PRODUCTS ||--o{ INVENTORY_MOVEMENTS : "tracked_by"
    ORDERS ||--|{ ORDER_ITEMS : "contains"

    USERS {
        uuid id PK
        varchar email UK "NOT NULL"
        varchar hashed_password "Argon2id"
        varchar full_name
        varchar role "CHECK (admin | customer)"
        boolean is_active "DEFAULT true"
        timestamptz created_at
        timestamptz updated_at
    }

    PRODUCTS {
        uuid id PK
        varchar sku UK "NOT NULL"
        varchar name "INDEXED"
        text description
        numeric price "CHECK (price >= 0)"
        integer stock_quantity "CHECK (stock_quantity >= 0)"
        boolean is_active "Soft Delete flag"
        timestamptz created_at
        timestamptz updated_at
    }

    ORDERS {
        uuid id PK
        uuid user_id FK
        varchar status "PENDING | CONFIRMED | CANCELLED"
        numeric total_amount "CHECK (total_amount >= 0)"
        timestamptz created_at
        timestamptz updated_at
    }

    ORDER_ITEMS {
        uuid id PK
        uuid order_id FK
        uuid product_id FK
        varchar product_name_snapshot "Immutable snapshot"
        numeric unit_price "Immutable snapshot >= 0"
        integer quantity "CHECK (quantity > 0)"
        numeric subtotal "CHECK (subtotal >= 0)"
    }

    INVENTORY_MOVEMENTS {
        uuid id PK
        uuid product_id FK
        varchar type "IN | OUT | ADJUSTMENT | RETURN"
        integer quantity "CHECK (quantity > 0)"
        integer previous_stock "CHECK (previous_stock >= 0)"
        integer new_stock "CHECK (new_stock >= 0)"
        varchar reference_id "Order ID or Document Ref"
        varchar reason "Audit reason"
        uuid created_by FK
        timestamptz created_at "Append-only (Immutable Trigger)"
    }

    IDEMPOTENCY_KEYS {
        uuid id PK
        uuid user_id FK "UNIQUE(user_id, key)"
        varchar key "UNIQUE(user_id, key)"
        varchar request_hash "SHA-256 payload digest"
        varchar status "PROCESSING | COMPLETED | FAILED"
        integer response_code
        jsonb response_body "Cached OrderResponse"
        timestamptz created_at
        timestamptz expires_at
    }
```

---

### 2. Sequence Diagram: Atomic Purchase Transaction

```mermaid
sequenceDiagram
    autonumber
    actor Client as Client / Browser
    participant API as FastAPI (Order Endpoint)
    participant Svc as OrderService
    participant DB as PostgreSQL 16 (ACID)

    Client->>API: POST /api/v1/orders (Header: Idempotency-Key)
    API->>Svc: create_order_atomic(user_id, payload, idempotency_key)
    Svc->>Svc: Compute canonical SHA-256 request_hash

    Svc->>DB: BEGIN TRANSACTION + SET LOCAL lock_timeout = '5000ms'
    Svc->>DB: SELECT * FROM idempotency_keys WHERE user_id = :u AND key = :k

    alt Key exists with differing request_hash
        DB-->>Svc: Existing key found (hash mismatch)
        Svc->>DB: ROLLBACK
        Svc-->>API: Raise IdempotencyConflictError
        API-->>Client: 409 Conflict (IDEMPOTENCY_CONFLICT)
    else Key exists with status = COMPLETED and matching hash
        DB-->>Svc: Existing key found (response_body JSONB)
        Svc->>DB: COMMIT (read-only commit)
        Svc-->>API: OrderResponse (cached)
        API-->>Client: 201 Created (Idempotent replay without double deduction)
    else New Idempotency Key
        Svc->>DB: INSERT INTO idempotency_keys (status='PROCESSING') + FLUSH
        Svc->>DB: SELECT * FROM products WHERE id IN (...) ORDER BY id ASC FOR UPDATE
        DB-->>Svc: Rows locked in ascending primary key order (Deadlock prevention)

        alt Inactive product or Insufficient stock in any item
            Svc->>DB: AUTOMATIC ROLLBACK (reverts idempotency key and releases locks)
            Svc-->>API: Raise InsufficientStockError / ConflictError
            API-->>Client: 409 Conflict (INSUFFICIENT_STOCK)
        else All items have sufficient stock
            Svc->>DB: UPDATE products SET stock_quantity = stock_quantity - :qty
            Svc->>DB: INSERT INTO orders (status='CONFIRMED', total_amount)
            Svc->>DB: INSERT INTO order_items (unit_price, product_name_snapshot)
            Svc->>DB: INSERT INTO inventory_movements (type='OUT', previous_stock, new_stock)
            Svc->>DB: UPDATE idempotency_keys SET status='COMPLETED', response_body=:json
            Svc->>DB: COMMIT TRANSACTION
            DB-->>Svc: Transaction committed
            Svc-->>API: OrderResponse
            API-->>Client: 201 Created (OrderResponse)
        end
    end
```

---

## 📚 Architecture Decision Records (ADRs)

Core architectural choices are documented in [`docs/adr`](docs/adr):

- [**ADR-001: PostgreSQL as Single Source of Truth for Transactional Idempotency**](docs/adr/ADR-001-postgresql-idempotency.md)
- [**ADR-002: Pessimistic Concurrency Control with `SELECT FOR UPDATE` and Deterministic Ordering**](docs/adr/ADR-002-select-for-update-concurrency.md)
- [**ADR-003: Immutable Double-Entry Ledger (`InventoryMovement`) and Historical Snapshots**](docs/adr/ADR-003-immutable-inventory-movements.md)

---

## 🖥️ StockFlow Dashboard (Web Admin Interface)

StockFlow includes a responsive **Single Page Application (SPA)** in [`frontend/`](frontend) built with **React, TypeScript, Vite, and Tailwind CSS**:

- **Real-Time KPIs:** Live overview metrics (Active SKUs, Physical Stock Units, Low Stock Alert `< 5`, Confirmed Orders, and Total Revenue).
- **Product Catalog Management:** Dynamic search by name or SKU, server pagination, and soft deletion.
- **Sales Terminal & Idempotency Testing:** Multi-item cart builder with customizable `Idempotency-Key` headers. Allows visual validation of duplicate prevention and `409 Conflict` scenarios.
- **Immutable Audit Ledger:** Visual feed of stock modifications (`IN`, `OUT`, `ADJUSTMENT`, `RETURN`) backed by PostgreSQL's append-only trigger.
- **Quick Demo Login:** One-click shortcuts to authenticate as **Administrator** or **Customer**.

---

## 🗂️ Project Structure

```text
StockFlow API/
├── .github/workflows/main.yml       # CI/CD Pipeline (Ruff, Mypy, Pytest w/ Postgres, Docker Build)
├── docs/adr/                        # Architecture Decision Records (ADR-001 to ADR-003)
├── frontend/                        # React + TypeScript + Vite + Tailwind CSS Dashboard
│   ├── src/
│   │   ├── components/              # Sidebar, Header, LoginModal
│   │   ├── context/                 # AuthContext (JWT session management)
│   │   ├── services/                # Typed API client
│   │   ├── views/                   # Dashboard, Catalog, Orders, Ledger
│   │   └── types/                   # API TypeScript contract interfaces
│   ├── Dockerfile
│   └── nginx.conf
├── src/stockflow/
│   ├── api/
│   │   ├── dependencies.py          # Database sessions, JWT auth, and RBAC guards
│   │   └── v1/
│   │       ├── endpoints/           # REST endpoints (/health, /dashboard, /auth, /products, /orders, /inventory)
│   │       └── router.py            # API v1 aggregator
│   ├── core/
│   │   ├── config.py                # pydantic-settings (SQLite strictly prohibited)
│   │   ├── exceptions.py            # Standardized HTTP error responses (401, 403, 404, 409, 422)
│   │   └── security.py              # Argon2id password hashing and JWT token handling
│   ├── db/
│   │   ├── base.py                  # SQLAlchemy 2.0 DeclarativeBase and naming conventions
│   │   ├── session.py               # AsyncEngine (asyncpg) and AsyncSessionLocal
│   │   └── migrations/              # Alembic migrations & PostgreSQL immutability trigger
│   ├── models/                      # SQLAlchemy 2.0 ORM Models
│   ├── schemas/                     # Strict Pydantic v2 validation models
│   ├── services/                    # Business rules and atomic transaction flows
│   └── main.py                      # FastAPI application entrypoint
├── tests/
│   ├── conftest.py                  # Fixtures wired strictly to real PostgreSQL
│   ├── unit/                        # Security and hashing unit tests
│   └── integration/                 # Concurrency stress tests (asyncio.gather) and flow tests
├── docker-compose.yml
├── Dockerfile
└── pyproject.toml
```

---

## 🚀 Running the Project

### Option 1: Via Docker Compose (Recommended)

```bash
# 1. Copy environment variables
cp .env.example .env

# 2. Build and start PostgreSQL, FastAPI Backend, and Web Dashboard
docker compose up --build -d

# 3. Seed demo catalog and administrator account
docker compose exec api python -m stockflow.seed
```

- **StockFlow Dashboard (Web UI):** `http://localhost:3000`
- **FastAPI Backend:** `http://localhost:8000`
- **Interactive Documentation (Swagger UI):** `http://localhost:8000/docs`
- **Deep Health Check:** `http://localhost:8000/health`

### Option 2: Local Development with Poetry

```bash
# 1. Install dependencies
poetry install

# 2. Start PostgreSQL service
docker compose up -d db

# 3. Run database migrations
poetry run alembic upgrade head

# 4. Seed demo data
poetry run python -m stockflow.seed

# 5. Start the FastAPI server
poetry run uvicorn stockflow.main:app --reload

# 6. Start the frontend (in another terminal)
cd frontend
npm install
npm run dev
```

---

## 🧪 Testing & Concurrency Verification

All tests run strictly against a **real PostgreSQL instance** (SQLite is forbidden by design in `Settings` and `conftest.py`).

```bash
# Run the entire test suite (Unit + Integration + Concurrency)
poetry run pytest -v

# Run the concurrency stress test (10 simultaneous requests for 5 items)
poetry run pytest tests/integration/test_concurrency.py -v

# Run multi-product cart order lifecycle test
poetry run pytest tests/integration/test_multi_product_order_flow.py -v

# Run Linter (Ruff) and Strict Type Checker (Mypy)
poetry run ruff check src tests
poetry run mypy src tests
```

---

## 📡 API Reference Overview

| Method | Endpoint | Auth | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Public | Real database connectivity check (`SELECT 1`) |
| `GET` | `/api/v1/dashboard/summary` | Public / Auth | Aggregated inventory KPIs, recent orders, and ledger movements |
| `POST` | `/api/v1/auth/register` | Public | Customer account registration (`role` injection is blocked) |
| `POST` | `/api/v1/auth/login` | Public | JSON login issuing a short-lived signed JWT |
| `GET` | `/api/v1/auth/me` | Authenticated | Current user profile |
| `POST` | `/api/v1/products` | **Admin** | Create catalog product and generate initial inventory movement |
| `GET` | `/api/v1/products` | Public / Auth | List products with pagination (`limit`/`offset`) and search (`name`/`sku`) |
| `PATCH` | `/api/v1/products/{id}` | **Admin** | Update product metadata and price |
| `DELETE` | `/api/v1/products/{id}` | **Admin** | **Soft delete** (`is_active = False`), preserving historical integrity |
| `POST` | `/api/v1/orders` | Authenticated | Atomic order purchase (`SELECT FOR UPDATE`) with `Idempotency-Key` |
| `GET` | `/api/v1/orders` | Authenticated | List orders with preserved historical line snapshots |
| `POST` | `/api/v1/inventory/movements` | **Admin** | Append manual stock movement (`IN`, `OUT`, `ADJUSTMENT`, `RETURN`) |
| `GET` | `/api/v1/inventory/movements` | Authenticated | Query immutable audit log of inventory movements |

---

## 📄 License

Licensed under the [MIT License](LICENSE).

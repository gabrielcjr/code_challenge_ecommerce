# Enterprise-Grade Django + HTMX E-Commerce SPA

Enterprise-grade e-commerce application built with Python 3.12, Django 5.2, HTMX 2, Tailwind CSS v4, and PostgreSQL 18.

## Quickstart

To launch the complete application with a single command:

```bash
git clone https://github.com/gabrielcjr/code_challenge_ecommerce.git
cd code_challenge_ecommerce
docker compose up --build
```

Open **[http://localhost:8000/](http://localhost:8000/)**. That is the whole setup.
No `.env` to copy, no migration to run, no seed command: the entrypoint migrates,
builds assets and loads a starting catalog on first boot, and CI verifies that a
clean checkout serves a populated dashboard with no manual steps.

## Features

- **Product CRUD** via HTMX modals with server-side fragment rendering
- **CSV Import** streaming parse, batched bulk upsert, capped row-level error reporting, drag-and-drop upload
- **Trigram-Optimized Search** PostgreSQL `pg_trgm` + GinIndex for fuzzy search, debounced HTMX live search (`keyup changed delay:300ms`)
- **Stock-Managed Checkout** simulated payment engine with 5% failure simulation, atomic `select_for_update` locking, inventory race condition handling
- **SPA UX without JS framework** Tailwind CSS v4 compiled via `@tailwindcss/cli`, HTMX 2 for fragment swaps
- **Tested Concurrency** threaded oversell, deadlock and lock-contention tests against PostgreSQL
- **Streaming CSV Import** lazy row iteration with batched bulk upserts, memory bounded by batch not file size

## Architecture & Technical Decisions

### 1. Service Layer Pattern Isolation (`services.py`)
- **Decision**: Decoupled core business rules from Django view controllers into dedicated domain service modules (`ProductService`, `OrderService`, `PaymentService`).
- **Rationale**: Views remain thin and focused on HTTP/HTMX fragment rendering. Service methods can be executed, tested, and reused in isolation without HTTP request overhead.

### 2. HTMX 2 Server-Driven SPA UX
- **Decision**: Built a dynamic Single Page Application (SPA) UX using server-side HTML fragment rendering via HTMX 2 and Tailwind CSS v4, avoiding heavy JavaScript client frameworks (React/Next.js).
- **Rationale**: Eliminates client-side state duplication, CORS complexity, and build tool chains while delivering an instantaneous, reactive SPA user experience.

### 3. PostgreSQL Trigram Search (`pg_trgm` + `GinIndex`) & Substring Fallback
- **Decision**: Search prioritizes exact SKU and substring matches first (`icontains`), falling back to PostgreSQL trigram similarity (`similarity__gt=0.2`).
- **Rationale**: Avoids the infrastructure complexity of ElasticSearch or Solr. Native PostgreSQL `pg_trgm` provides fast fuzzy typo matching while exact matching ensures exact SKU queries (e.g., `PRJ-001`) return precise single results.

### 4. Inventory Concurrency & Race Condition Defense (`select_for_update`)
- **Decision**: Order creation and stock reduction run inside an atomic transaction (`transaction.atomic()`) with row-level locks taken in a deterministic `order_by("id")` sequence.
- **Rationale**: Prevents overselling when concurrent buyers race for the last units. Ordering the lock acquisition also prevents deadlocks between two multi-product orders that touch the same products in opposite order.
- **Evidence**: `apps/orders/tests/test_concurrency.py` drives 20 threads at 10 units of stock and asserts exactly 10 succeed, 10 are rejected, and stock lands on 0. Dropping `select_for_update()` drives stock to **-18** and the suite fails, so the tests fail for the right reason rather than passing vacuously.
- **Known trade-off**: the simulated payment call happens while the row locks are held, which is the correct choice for a synchronous fake gateway but would need reworking into a reserve/confirm flow against a real provider whose latency you do not control.

### 5. CSV Import Memory Profile (streaming + batched upserts)
- **Decision**: The importer pulls rows lazily through `io.TextIOWrapper` and flushes them in batches of 500 via `bulk_create`/`bulk_update`, each batch in its own transaction. Error reports are capped at 200 rows.
- **Rationale**: The obvious implementation (`csv_file.read().decode()`) holds the entire upload in memory twice and issues one SELECT plus one write per row inside a single file-long transaction. Peak memory is now bounded by the batch size rather than the file size, and a malformed 10-million-row file cannot grow an unbounded error report.
- **Trade-off**: Batching means a row rejected by validation is skipped rather than aborting the whole import, so a partially valid file lands its valid rows. That matches the challenge CSV, which deliberately contains bad rows. An all-or-nothing import would need a single wrapping transaction and would reintroduce the long-transaction cost.
- **Evidence**: `apps/products/tests/test_services.py::CSVImportMemoryTest` imports 2000 rows and asserts the query count stays proportional to batches rather than rows, and feeds the importer a non-seekable 8KB-buffered stream to prove nothing reads the file whole.

### 6. Security & Input Sanitization Pipeline
- **Decision**: CSV imports pass through `_sanitize_input_text()` to strip HTML tags (`strip_tags`) and leading formula characters (`=`, `+`, `@`, `\t`, `\r`).
- **Rationale**: Protects against Cross-Site Scripting (XSS), CSV Formula Injection in Excel/Google Sheets, and SQL injection (via Django ORM parameterized queries).

### 7. Containerization & CI Alignment
- **Decision**: GitHub Actions CI workflow runs code linters (`make run-check-linters`) and test suites (`python manage.py test`) directly inside the Docker Compose container stack.
- **Rationale**: Ensures 100% environment parity between local development, CI runner, and production deployments.

### 8. No Code Comments Constraint
- **Decision**: Enforced clean code principles with zero inline or block comments across all `.py`, `.html`, `.css`, `.js`, `.yml`, `Dockerfile`, and `Makefile` files.
- **Rationale**: Ensures clear, self-documenting code with explicit variable and method naming.

## Project Structure

```
config/           Django settings, urls, wsgi/asgi
apps/products/    Product domain: model, service, forms, views, urls
apps/orders/      Order domain: Order, OrderItem, PaymentService, OrderService
templates/
  base.html       Enterprise shell, navigation, modal target, toast
  products/list.html  Dashboard with live search + filters
  products/partials/  Table, form modal, csv modal, detail modal, import result
  orders/partials/    Checkout modal, order success
static/
  css/src/input.css   Tailwind v4 directive
  js/htmx.min.js      HTMX 2.0.4
```

## Running the Project

### The only required step

```bash
git clone https://github.com/gabrielcjr/code_challenge_ecommerce.git
cd code_challenge_ecommerce
docker compose up --build
```

Open [http://localhost:8000/](http://localhost:8000/). There is no `.env` to copy,
no migration to trigger and no seed command to remember. The container entrypoint
runs migrations, collects static assets and loads a catalog on first boot, so the
dashboard has products in it the moment the page renders. CI asserts exactly this:
a clean checkout must answer HTTP 200 with a non-empty catalog and zero setup steps.

`.env` is optional. Compose ships working defaults for every variable; copy
`.env.example` to `.env` only when you want to override them.

### First-boot catalog

`manage.py bootstrap_data` runs automatically and is idempotent, so restarts never
duplicate or clobber data:

1. If `Code Challenge E-Commerce.csv` sits in the project root, it is imported.
2. Otherwise the built-in sample catalog is seeded.
3. If products already exist, it does nothing.

Reload the challenge CSV at any time with
`docker compose exec web python manage.py bootstrap_data --force`, or through the
drag-and-drop CSV import in the UI.

### Running without Docker

Docker is the supported path. If you need a host install: Python 3.12, a reachable
PostgreSQL 18, `pip install -r requirements.txt`, then `python manage.py migrate &&
python manage.py bootstrap_data && python manage.py runserver`. Set
`USE_SQLITE_FOR_TESTS=1` to fall back to SQLite, which is fine for the unit tests but
cannot run the concurrency suite (see below).

### Linting

```bash
make run-check-linters
# or individually:
make run-check-flake8
make run-check-black
make run-check-isort

make run-fix-linters
```

### Tests

```bash
make docker-test              # full suite against PostgreSQL, this is the real one
make docker-test-concurrency  # only the inventory race-condition suite
make test                     # SQLite, fast, skips the concurrency suite
```

The concurrency tests are `TransactionTestCase`-based and require row-level locking,
so they are guarded by `@skipUnlessDBFeature("has_select_for_update")` and silently
skip on SQLite. Run them against PostgreSQL or they prove nothing.

CI (`.github/workflows/ci.yml`) runs linters and the full suite inside the Compose
stack against PostgreSQL 18, so the concurrency tests always execute there.

## API / Routes

- `/` product list dashboard with search fragments
- `/search/` HTMX fragment endpoint for product table
- `/products/create/modal/` + `/products/create/` create flow
- `/products/<id>/edit/modal/` + `/products/<id>/edit/` update flow
- `/products/<id>/delete/` delete
- `/products/import/modal/` + `/products/import/` CSV import
- `/orders/checkout/<id>/modal/` + `/orders/checkout/<id>/` checkout
- `/orders/` order list
- `/orders/<txn_id>/` order detail

## Sample CSV & Evaluation Dataset

- **CSV Download Date**: **July 30, 2026**
- **Provided Example File**: `Code Challenge E-Commerce.csv` (98 lines of evaluation test cases including currency formats, XSS payloads, SQL injection benchmarks, and whitespace validation). Drop it in the project root before the first `docker compose up` and it is imported automatically; otherwise the built-in sample catalog is seeded instead.
- **Sample Reference File**: `sample_products.csv` (10 clean product rows adhering to the required schema: name, sku, description, category, price, stock, weight_kg).

## Domain Models

**Product**: name, sku (unique, indexed), description, category (choices), price, stock, weight_kg, created_at, updated_at

**Order**: transaction_id (uuid), customer_name, customer_email, total_amount, payment_status (PAID/FAILED/PENDING), timestamps + prefetch items

**OrderItem**: FK order, FK product (PROTECT), quantity, unit_price (historical), subtotal property

## Alternatives Considered

- **Next.js frontend** rejected due to requirement for HTMX + server fragment architecture, lower build overhead, enterprise SSR simplicity
- **ElasticSearch** for search rejected in favor of native Postgres trigram which satisfies fuzzy search without extra infrastructure
- **Celery for payment** not needed for simulation, sync processing with atomic transaction sufficient; can be extended to async later
- **DRF API** not needed as UI uses HTML fragments, keeps stack simple; could add later for mobile clients

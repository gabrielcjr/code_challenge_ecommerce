# Enterprise-Grade Django + HTMX E-Commerce SPA

Enterprise-grade e-commerce application built with Python 3.12, Django 5.2, HTMX 2, Tailwind CSS v4, and PostgreSQL 18.

## Quickstart

To launch the complete application with a single command:

```bash
# 1. Clone the repository
git clone https://github.com/gabrielcjr/code_challenge_ecommerce.git
cd code_challenge_ecommerce

# 2. Copy environment settings
cp .env.example .env

# 3. Launch with Docker Compose
docker compose up -d --build
```

Access the application in your browser at **[http://localhost:8000/](http://localhost:8000/)**.
Database setup, migrations, and asset compilation run automatically inside Docker!

## Features

- **Product CRUD** via HTMX modals with server-side fragment rendering
- **CSV Import** atomic batch upsert with row-level error reporting
- **Trigram-Optimized Search** PostgreSQL `pg_trgm` + GinIndex for fuzzy search, debounced HTMX live search (`keyup changed delay:300ms`)
- **Stock-Managed Checkout** simulated payment engine with 5% failure simulation, atomic `select_for_update` locking, inventory race condition handling
- **SPA UX without JS framework** Tailwind CSS v4 compiled via `@tailwindcss/cli`, HTMX 2 for fragment swaps
- **Comprehensive Tests** unit + integration + E2E workflow tests

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
- **Decision**: Order creation and stock reduction run inside an atomic transaction (`transaction.atomic()`) with row-level locks (`select_for_update()`).
- **Rationale**: Prevents inventory overselling and race conditions when multiple concurrent users purchase remaining stock items simultaneously.

### 5. Security & Input Sanitization Pipeline
- **Decision**: CSV imports pass through `_sanitize_input_text()` to strip HTML tags (`strip_tags`) and leading formula characters (`=`, `+`, `@`, `\t`, `\r`).
- **Rationale**: Protects against Cross-Site Scripting (XSS), CSV Formula Injection in Excel/Google Sheets, and SQL injection (via Django ORM parameterized queries).

### 6. Containerization & CI Alignment
- **Decision**: GitHub Actions CI workflow runs code linters (`make run-check-linters`) and test suites (`python manage.py test`) directly inside the Docker Compose container stack.
- **Rationale**: Ensures 100% environment parity between local development, CI runner, and production deployments.

### 7. No Code Comments Constraint
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

## Local Execution

### Prerequisites
- Python 3.11+ (3.12 recommended)
- PostgreSQL 18 (or SQLite fallback for tests via `USE_SQLITE_FOR_TESTS=1`)
- Node.js 20 for Tailwind CLI (optional, CDN fallback in base.html)

### Setup

```bash
pip install -r requirements.txt

# Configure database via env or use defaults:
# POSTGRES_DB=ecommerce POSTGRES_USER=postgres POSTGRES_PASSWORD=postgres POSTGRES_HOST=localhost

# For quick local test without Postgres:
USE_SQLITE_FOR_TESTS=1 python manage.py migrate
USE_SQLITE_FOR_TESTS=1 python manage.py seed --refresh

# With Postgres:
python manage.py migrate
python manage.py seed --refresh

# Tailwind build (optional, CDN used as fallback):
npm install
npx @tailwindcss/cli -i ./static/css/src/input.css -o ./static/css/dist/output.css --minify

python manage.py runserver 0.0.0.0:8000
```

### Docker

```bash
docker-compose up --build
# App at http://localhost:8000
# DB at localhost:5432

docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py seed --refresh
```

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
# Using SQLite for CI without Postgres:
USE_SQLITE_FOR_TESTS=1 python manage.py test --verbosity=2

# Using Postgres:
python manage.py test

make test
```

CI pipeline `.github/workflows/ci.yml` runs linters + tests against Postgres 18 service container on push/PR.

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
- **Provided Example File**: `Code Challenge E-Commerce.csv` (98 lines of evaluation test cases including currency formats, XSS payloads, SQL injection benchmarks, and whitespace validation).
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

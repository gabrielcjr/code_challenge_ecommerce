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

## Architecture Decisions

### Service Layer Isolation
Business logic isolated in `services.py`:
- `ProductService.list_products()` handles filtering, trigram search fallback, pagination
- `ProductService.import_products_from_csv()` atomic transaction, schema validation, upsert by SKU
- `OrderService.create_and_process_order()` locks products via `select_for_update`, invokes `PaymentService`, creates order + items, decrements stock atomically
- `PaymentService` simulates external gateway with optional failure mode

Thin views delegate to services and return HTML fragments for HTMX requests vs full pages.

### HTMX Fragment Strategy
- Base layout provides `#modal-container` and `#product-table-container`
- Search form uses `hx-get` + `hx-trigger="change, keyup changed delay:300ms"` + `hx-target="#product-table-container"`
- CRUD modals rendered via `hx-get` to modal endpoints, forms `hx-post` back to table container
- Custom events `productCreated`, `productUpdated`, `csvImported` trigger toast + modal close

### PostgreSQL Optimization
- `sku` db_index for fast lookup during CSV upsert
- Trigram index via `GinIndex` with `gin_trgm_ops` would be added in migration when using PostgreSQL (fallback to `icontains` when `pg_trgm` unavailable or SQLite)
- `select_for_update` in order service prevents race conditions

### No Code Comments Constraint
Self-documenting code, clean naming, explicit service methods.

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

## Sample CSV

`sample_products.csv` provides 10 products adhering to schema: name, sku, description, category, price, stock, weight_kg

## Domain Models

**Product**: name, sku (unique, indexed), description, category (choices), price, stock, weight_kg, created_at, updated_at

**Order**: transaction_id (uuid), customer_name, customer_email, total_amount, payment_status (PAID/FAILED/PENDING), timestamps + prefetch items

**OrderItem**: FK order, FK product (PROTECT), quantity, unit_price (historical), subtotal property

## Alternatives Considered

- **Next.js frontend** rejected due to requirement for HTMX + server fragment architecture, lower build overhead, enterprise SSR simplicity
- **ElasticSearch** for search rejected in favor of native Postgres trigram which satisfies fuzzy search without extra infrastructure
- **Celery for payment** not needed for simulation, sync processing with atomic transaction sufficient; can be extended to async later
- **DRF API** not needed as UI uses HTML fragments, keeps stack simple; could add later for mobile clients

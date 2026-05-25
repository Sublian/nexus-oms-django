# Installation — Nexus OMS

> Setup guide for the Nexus OMS local development environment — a multi-tenant OMS platform with electronic invoicing, built on Django, DRF, HTMX, and Celery.

📘 Spanish version: [`docs/installation.es.md`](installation.es.md)

**Recommended method: Docker Compose.**

---

## Requirements

| Tool | Version |
| :--- | :--- |
| Git | Latest |
| Docker | 24+ |
| Docker Compose | v2+ |
| Python | 3.12+ *(non-Docker only)* |
| PostgreSQL | 17 *(non-Docker only)* |
| Redis | 7 *(non-Docker only)* |

---

## Quick Start (5 minutes)

Full stack with realistic demo data, up in a single flow.

```bash
git clone https://github.com/Sublian/nexus-oms-django.git
cd nexus-oms-django
cp .env.example .env
docker compose up --build -d
docker compose exec web python manage.py migrate
docker compose exec web python manage.py seed_data --orders 50
```

### Access Points

| Service | URL |
| :--- | :--- |
| App | http://localhost:8000 |
| Django Admin | http://localhost:8000/admin |
| Operational Dashboard | http://localhost:8000/dashboard/adidas/operations/ |

---

## Demo Credentials

The `seed_data` command auto-generates a complete operational environment.

### Superuser

| Field | Value |
| :--- | :--- |
| Email | `superadmin@nexus.com` |
| Password | `admin123` |

### Demo Organizations (Tenants)

5 independent tenants are created automatically:

| Organization | Slug |
| :--- | :--- |
| Tienda Principal | `tienda-principal` |
| Nike | `nike` |
| Adidas | `adidas` |
| Minorista | `minorista` |
| Mykonos Shop | `mykonos-shop` |

Each tenant includes isolated catalog, customers, inventory, multi-state orders, payments, mock SUNAT invoicing, and operational analytics data.

---

## Installation with Docker (Recommended)

### 1. Clone the repository

```bash
git clone https://github.com/Sublian/nexus-oms-django.git
cd nexus-oms-django
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Minimum required variables:

```env
SECRET_KEY=<your-secret-key>
DEBUG=True
DATABASE_URL=postgres://nexus_user:nexus_pass@db:5432/nexus_db
REDIS_URL=redis://redis:6379/0
CELERY_TASK_ALWAYS_EAGER=False
```

Generate a `SECRET_KEY`:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

### 3. Start services

```bash
docker compose up --build -d
```

Included services:

| Service | Description |
| :--- | :--- |
| `web` | Django + Gunicorn dev server |
| `worker` | Celery worker |
| `db` | PostgreSQL 17 |
| `redis` | Redis 7 |

### 4. Apply migrations

```bash
docker compose exec web python manage.py migrate
```

### 5. Load demo data

```bash
docker compose exec web python manage.py seed_data --orders 50
```

### 6. Verify services

```bash
docker compose ps
```

All services should show status `running`.

---

## Installation without Docker

Requires PostgreSQL 17 and Redis 7 running locally.

### 1. Clone and create virtual environment

```bash
git clone https://github.com/Sublian/nexus-oms-django.git
cd nexus-oms-django
python -m venv .venv
```

Activate:

```bash
# Linux/macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure `.env`

```bash
cp .env.example .env
```

Local example:

```env
DATABASE_URL=postgres://nexus_user:nexus_pass@localhost:5432/nexus_db
REDIS_URL=redis://localhost:6379/0
```

### 4. Create database

```sql
CREATE USER nexus_user WITH PASSWORD 'nexus_pass';
CREATE DATABASE nexus_db OWNER nexus_user;
```

### 5. Apply migrations

```bash
python manage.py migrate
```

### 6. Load demo data

```bash
python manage.py seed_data --orders 50
```

### 7. Start Django

```bash
python manage.py runserver
```

### 8. Start Celery (separate terminal)

```bash
celery -A config worker --loglevel=info
```

---

## Seed Data

`seed_data` generates a complete operational environment for development and testing.

### What it generates (per tenant)

- Products, categories, stock, warehouses
- Customers
- Orders with multiple states
- Payments
- Mock SUNAT invoicing
- Mock SUNAT sync queue
- External integration logs
- Operational metrics
- Demo accounting data

### Temporal distribution

Orders are distributed across the **last 60 days** to feed KPIs, dashboard, time series, analytics, and charts accurately.

### Included states

**Orders**

| State | Description |
| :--- | :--- |
| `PAID` | Payment confirmed |
| `SHIPPED` | In transit |
| `DELIVERED` | Delivery confirmed |
| `COMPLETED` | Cycle complete |

**Electronic invoicing**

| State | Description |
| :--- | :--- |
| `pending` | Awaiting sync |
| `accepted` | SUNAT accepted |
| `rejected` | SUNAT rejected |
| `failed` | Provider error |

**SUNAT queue**

| State | Description |
| :--- | :--- |
| `pending` | In queue |
| `processing` | Being processed |
| `completed` | Synced successfully |
| `dead_letter` | Terminal error |
| `exhausted` | Retries exhausted |

### Examples

```bash
# Minimal load
python manage.py seed_data --orders 5 --clients 3

# Heavy load
python manage.py seed_data --orders 200 --clients 100
```

---

## Electronic Invoicing (Current Status)

Nexus OMS currently uses a **mock provider** compatible with the SUNAT/Nubefact flow.

Current goals:

- Simulate real operational pipelines
- Validate dashboards and queue visibility
- Generate representative metrics
- Test retry and dead letter workflows
- Detect accounting inconsistencies
- Visualize operational errors

Real SUNAT/Nubefact integration will be implemented via decoupled adapters — no domain changes required.

---

## Operational Dashboard

The multi-tenant operational dashboard is available at:

```
/dashboard/<tenant>/operations/
```

Includes: invoicing KPIs, SUNAT acceptance rate, sync queue depth, dead letters, external integrations, per-provider error rate, average latency, accounting consistency, time series, and date filters.

---

## Testing

```bash
# Full test suite
docker compose exec web pytest

# With coverage
docker compose exec web pytest --cov
```

---

## Useful Commands

| Action | Command |
| :--- | :--- |
| View logs | `docker compose logs -f` |
| Stop stack | `docker compose down` |
| Restart services | `docker compose restart` |
| Django shell | `docker compose exec web python manage.py shell` |
| Run tests | `docker compose exec web pytest` |
| Coverage | `docker compose exec web pytest --cov` |
| Create migrations | `docker compose exec web python manage.py makemigrations` |
| Apply migrations | `docker compose exec web python manage.py migrate` |

---

## Troubleshooting

**PostgreSQL won't start**

```bash
docker compose down -v
docker compose up --build
```

**Redis connection refused**

```bash
docker compose ps
```

Verify all services are running.

**Inconsistent migrations**

```bash
docker compose exec web python manage.py migrate
```

**Dashboard appears empty**

```bash
docker compose exec web python manage.py seed_data --orders 50
```

---

## Project Structure

```text
nexus-oms-django/
├── src/
│   ├── domain/          # Business models and domain logic
│   ├── application/     # Use cases and analytics services
│   ├── infrastructure/  # Celery, adapters, providers
│   └── interfaces/      # DRF API + HTMX views
│
├── config/              # Django settings + Celery config
├── docs/                # ADRs, roadmap, documentation
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## Notes

> ⚠️ Never commit `.env` to the repository.

**Production requirements:**

- `DEBUG=False`
- Gunicorn + Nginx
- Managed PostgreSQL
- Persistent Redis

**Architecture:** Clean Architecture · DDD · Service Layer · HTMX-first UI · Event-driven tasks with Celery

---

## Related Documentation

| Document | Description |
| :--- | :--- |
| [`README.md`](../README.md) | Project overview |
| [`docs/README.es.md`](README.es.md) | Full Spanish README |
| [`docs/operational_roadmap.md`](operational_roadmap.md) | Operational roadmap |
| [`docs/architecture.md`](architecture.md) | Architecture and technical decisions |
| [`docs/adrs/`](adrs/) | Architecture Decision Records |
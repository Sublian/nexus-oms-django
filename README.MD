# Nexus OMS — Enterprise Multi-Tenant Operational Commerce Platform

[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![Django Version](https://img.shields.io/badge/django-6.0%2B-green)](https://www.djangoproject.com/)
[![Architecture](https://img.shields.io/badge/architecture-Clean%20%2B%20DDD-orange)](#architecture)
[![Coverage](https://codecov.io/gh/Sublian/nexus-oms-django/branch/main/graph/badge.svg)](https://codecov.io/gh/Sublian/nexus-oms-django)
[![CI](https://github.com/Sublian/nexus-oms-django/actions/workflows/ci.yml/badge.svg)](https://github.com/Sublian/nexus-oms-django/actions/workflows/ci.yml)

> 📘 Spanish documentation available at [`docs/README.es.md`](docs/README.es.md)

High-performance **Order Management System** built for multi-tenant SaaS operations. Nexus enforces strict domain isolation, asynchronous workflows, and financial traceability — designed as a scalable foundation for Latin American commerce and electronic invoicing ecosystems.

---

## Architecture

Nexus follows **Clean Architecture** + **DDD** principles, with hard boundaries between domain logic and infrastructure.

```
src/
├── domain/             # Business models, domain rules, financial logic
├── application/        # Use cases & service orchestration
├── infrastructure/     # Async tasks, external adapters, DB configuration
├── interfaces/
│   ├── api/            # DRF REST endpoints
│   └── web/            # Django + HTMX reactive views
│
├── tests/              # 220+ automated tests
├── templates/          # Shared templates
├── .github/workflows/  # CI pipeline
├── docker-compose.yml  # Full dev stack
└── docs/               # ADRs, roadmap, architecture notes
```

### Layer Responsibilities

| Layer | Responsibility |
| :--- | :--- |
| **Domain** | Pure business entities, persistence models, financial logic |
| **Application** | Use case orchestration, service coordination |
| **Infrastructure** | Celery tasks, DB adapters, AWS config, external integrations |
| **Interface** | REST API (DRF) + reactive web views (HTMX) |

### Design Patterns

- **Strategy Pattern** — multi-channel notification system
- **Service Layer** — centralized business logic, decoupled from views
- **Adapter Pattern** — replaceable external integrations (invoicing providers, ERPs)
- **Mocker Pattern** — full isolation for async unit tests

---

## Core Systems

### Multi-Tenancy

Strict organization-level data isolation enforced at every layer:

- Middleware context propagation on every request
- Tenant-aware ORM query filtering via custom managers
- Scoped services — no cross-tenant data leakage by design
- Isolated analytics and dashboard KPIs per organization

### Order Management (OMS)

Full order lifecycle engine:

```
pending → paid → shipped → delivered → completed → returned
```

Supports delivery flows, store pickup, reverse logistics, payment reconciliation, and operational state transitions.

### Electronic Invoicing Pipeline (SUNAT-Ready)

Decoupled invoicing architecture with full auditability:

- Invoice state machine with async synchronization
- Retry workflows with dead letter queues
- Provider abstraction layer — swap providers without touching domain logic
- Current mock provider: **Nubefact** (adapter-ready)

### Financial Engine

`FinanceService` handles margin calculations, commissions, and real profitability — decoupled from order flow, reusable across contexts.

### Operational Dashboard

Built for operators, not administrators:

| KPI Area | Metrics |
| :--- | :--- |
| Invoicing | Daily series, acceptance rate, error rate |
| SUNAT Sync | Queue depth, retry count, dead letters |
| Providers | Latency, error distribution, availability |
| Accounting | Consistency validation, reconciliation status |

### External Integrations

Adapter-oriented integration layer with:

- Structured request/response logging
- Per-provider latency tracking
- Error metrics and operational visibility

Prepared adapters: **Nubefact**, **Shopify**, **WooCommerce**, **Migo** — extensible without core rewrites.

---

## Service Layer

| Service | Responsibility |
| :--- | :--- |
| `OrderService` | Order workflow transitions and business rules |
| `FinanceService` | Margin, commission, and profitability calculations |
| `DashboardKPIService` | Operational KPI aggregation per tenant |
| `DailyInvoiceSeriesService` | Invoice analytics and chart data |
| `DateRangeService` | Time-range filtering abstraction |

---

## Frontend Strategy

Server-side rendering with selective reactivity — no SPA overhead.

| Technology | Role |
| :--- | :--- |
| **Django Templates** | SSR — fast initial load, SEO-ready |
| **HTMX** | Partial DOM updates, AJAX without JS frameworks |
| **TailwindCSS** | Utility-first responsive styling |
| **Chart.js** | Analytics visualizations |
| **Alpine.js** | Minimal client-side interactivity |

---

## Tech Stack

| Component | Technology |
| :--- | :--- |
| **Backend** | Python 3.12+, Django 6 |
| **API** | Django REST Framework |
| **Frontend** | HTMX + TailwindCSS + Chart.js |
| **Database** | PostgreSQL |
| **Task Queue** | Celery + Redis |
| **Infrastructure** | Docker, AWS EC2 (Ubuntu + Nginx) |
| **Testing** | Pytest |
| **CI/CD** | GitHub Actions + Codecov |

---

## Testing

**220+ automated tests** covering:

- Domain services and business rules
- OMS workflow transitions
- Multi-tenant isolation
- Dashboard KPIs and analytics services
- Invoicing flows and retry logic
- URL resolution

Testing approach: deterministic services, isolated business logic, zero shared state between tenants in tests.

---

## Local Development

```bash
# Start full stack
docker compose up --build

# Run migrations
docker compose exec web python manage.py migrate

# Seed demo data
docker compose exec web python manage.py seed_data --orders 50

# Run test suite
docker compose exec web pytest
```

Full installation guide: [`docs/installation.md`](docs/installation.md)

---

## Implementation Status

| Area | Status |
| :--- | :--- |
| Multi-tenant architecture | ✅ Complete |
| OMS workflows | ✅ Complete |
| Financial calculations | ✅ Complete |
| Operational dashboard | ✅ Complete |
| Analytics services | ✅ Complete |
| Electronic invoicing pipeline | ✅ Complete |
| Queue observability | ✅ Complete |
| Integration logging | ✅ Complete |
| Async workflows | ✅ Complete |
| RBAC / granular permissions | 🔄 In progress |
| Real SUNAT adapters | 🔄 In progress |
| Inventory synchronization | 🔄 In progress |
| Advanced analytics | 🔄 In progress |
| Accounting workflows | 🔄 In progress |
| Operational audit screens | 🔄 In progress |

---

## Philosophy

> *"Keep the backend intelligent, the frontend thin, and the operations observable."*

Nexus is built to scale without rewriting. Business logic stays in the domain. Integrations stay replaceable. Operations stay visible.

---

*This project is under active private development.*
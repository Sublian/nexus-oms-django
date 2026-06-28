# Architecture Root — Nexus OMS

## ¿Qué es?

Arquitectura de **doble interfaz** (REST API + Web Dashboard) sobre base de dominio compartido. Implementa **Clean Architecture** + **Domain-Driven Design**.

```
┌─────────────────────────────────────────────────────────┐
│ Interfaces Layer                                         │
├───────────────────────┬─────────────────────────────────┤
│ REST API (/api/v1/)   │ Web Dashboard (/dashboard/)     │
│ DRF ViewSets          │ Django Views + HTMX             │
│ JWT Auth              │ Session Auth                    │
│ JSON Serializers      │ Form Serializers                │
└───────────────────────┴─────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────┐
│ Application Layer (Use Cases + Services)                │
│ - CreateInvoiceUseCase                                  │
│ - OrderWorkflowService                                  │
│ - InvoiceStatusQueryUseCase                             │
└─────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────┐
│ Domain Layer (Entities + Rules)                         │
│ - Order (FSM) + OrderItem                              │
│ - Invoice + InvoiceSyncQueue                            │
│ - Stock + StockMovement                                 │
│ - ExchangeRate, CompanyInvoiceConfig                    │
│ - Signals (stock adjustments)                           │
│ - Tasks (Celery)                                        │
└─────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────┐
│ Infrastructure Layer                                    │
├───────────────────────┬─────────────────────────────────┤
│ PostgreSQL (ORM)      │ Celery + Redis                  │
│ TenantManager         │ APIMigo Client                  │
│ Thread-local Context  │ WeasyPrint (PDF)                │
│ Multitenancy (M/T)    │ External APIs                   │
└───────────────────────┴─────────────────────────────────┘
```

## Stack Técnico

### Backend
- **Django 6.0.3** — Web framework
- **DRF 3.17.1** — REST API + Serializers
- **djangorestframework-simplejwt 5.4.0** — JWT auth
- **django-fsm 3.0.1** — Order state machine
- **psycopg3 3.3.3** — PostgreSQL driver

### Frontend
- **HTMX 1.27.0** — Real-time interactivity (no JavaScript)
- **Tailwind CSS (CDN)** — Styling
- **Django Templates** — Rendering

### Async & Infrastructure
- **Celery 5.6.3** — Distributed task queue
- **Redis** — Broker + caching
- **PostgreSQL** — Primary data store
- **WeasyPrint 68.1** — PDF generation

### Testing & DevOps
- **pytest 9.0.2** — Test runner
- **pytest-django** — Django ORM fixtures
- **pytest-cov** — Coverage tracking
- **Docker Compose** — Local stack
- **drf-spectacular 0.29.0** — Swagger/OpenAPI docs

## Directorios

```
src/
├── domain/              # Entities, FSM, services, signals, tasks
│   ├── models/         # Order, Invoice, Stock, etc.
│   ├── services/       # OrderService, FinanceService
│   ├── tasks/          # Celery tasks
│   ├── signals.py      # Stock adjustments
│   ├── exceptions.py   # Nubefact error taxonomy
│   └── constants.py    # Order states, invoice states
├── application/         # Orchestration (Use Cases, Workflows)
│   ├── usecases/       # CreateInvoiceUseCase, etc.
│   ├── services/       # OrderWorkflowService
│   └── providers/      # Invoice provider abstraction
├── infrastructure/      # Persistence, external APIs, M/T
│   ├── models.py       # TenantModel (abstract)
│   ├── multitenancy/   # Middleware, thread-local, TenantManager
│   └── services/       # APIMigoClient, etc.
└── interfaces/
    ├── api/            # DRF viewsets, serializers → /api/v1/
    └── web/            # Django views, templates → /dashboard/

config/
├── settings/           # base.py, local.py, testing.py, production.py
├── celery.py           # Celery app + autodiscover
└── urls.py             # Auth, API, web routes
```

## Autenticación

**API (JWT)**:
- `CustomTokenObtainPairSerializer` extiende JWT con `{email, role, organization_id}`
- Access token: 1h, Refresh: 7 días
- Tenant resuelto desde JWT claim `organization_id`

**Web (Sessions)**:
- Django sessions + custom user model `CustomUser`
- Tenant resuelto desde URL slug (`/dashboard/<org_slug>/`)
- Role-based access control (admin, manager, staff)

## Multi-Tenancy

Cada modelo que almacena datos por tenant hereda de `TenantModel`:
- Añade FK a `organization`
- Se filtra automáticamente via `TenantManager`
- Middleware setea `organization_id` en thread-local por request
- **INVARIANTE**: Nunca usar `.all_objects` en código de negocio

[Detalles en security/root.md](../security/root.md)

## ¿Por qué existe?

Nexus necesita:
1. **REST API** para SPA futura + integraciones externas
2. **Web Dashboard** para soporte interno + análisis
3. **Aislación multi-tenant** garantizada en ambas interfaces
4. **Escalabilidad asíncrona** via Celery para invoicing + reportes

## Relaciones

- [Domain](../domain/root.md) — Modelos + reglas que sustentan esta arquitectura
- [Security](../security/root.md) — Aislación + protecciones en cada capa
- [Infrastructure](../infrastructure/root.md) — Persistencia + async que ejecutan esta arquitectura

---

**Estado**: STABLE
**Última actualización**: 2026-06-27
**Responsable**: Tech Lead
**Siguiente nodo recomendado**: [domain/root.md](../domain/root.md)

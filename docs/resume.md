# Nexus OMS — Resumen de Avances del Proyecto
**Fecha de corte:** 19 de Junio, 2026 | **Versión:** 3.4.0-WIP | **Fase Activa:** SECTOR S (Security & Tenant Foundation) — DISCOVERY ✅ COMPLETE

---

## Estado General

| Sprint | Estado | Commits | Tests |
|--------|--------|---------|-------|
| Sprint 1 — Provider architecture + tenant config | ✅ COMPLETO | `3197ec9` | +7 |
| Sprint 2 — Async + locking + retry + NubefactClient | ✅ COMPLETO | `55cebbd`→`d061c77` | +48 |
| Sprint 3 Paso 1 — InvoiceSyncQueue + estados expandidos | ✅ COMPLETO | `1f9878f` | — |
| Sprint 3 Paso 2 — get_invoice_status + UseCase | ✅ COMPLETO | `2752990` | +29 |
| Sprint 3 Paso 3 — Tasks de polling + Beat schedule | ✅ COMPLETO | `906f9ed` | +19 |
| Sprint 3 Paso 4 — Wiring: create_invoice → InvoiceSyncQueue | ✅ COMPLETO | `caf6fdb`→`edb1298` | +2 |
| Mini-sprint Operational Visibility | ✅ COMPLETO | `5a09c33`→`f57cbc4` | — |
| Sprint 4 — Dashboard operacional | ✅ COMPLETO | `f0d6760`→`eb8560b` | — |
| Bloque A — Analytics tests (deuda técnica) | ✅ COMPLETO | `4fc016a` | +39 |
| FASE 1 — Date Range UX + labels español | ✅ COMPLETO | `7ad0d82` | 0 nuevos |
| FASE 2A — Drill-down operacional | ✅ COMPLETO | `99b52c3` | +22 |
| FASE 2B — Drill-down facturación (KPI interactivos) | ✅ COMPLETO | `9086ca6` | +8 |
| FASE 3 — Invoice Observable + Timeline + T6 Mitigation | ✅ COMPLETO | `cad877a` | +8 |
| FASE 3.4A — Discovery & Audit (Observability) | ✅ COMPLETO | audit only | — |
| FASE 3.4B-A — Root Cause Analysis (Test Failures) | ✅ COMPLETO | audit only | — |
| FASE 3.4B-B — Test Recovery (Fix & Verify) | ✅ COMPLETO | `c1abd64` | — |
| **SECTOR S — Security Discovery (S0)** | ✅ COMPLETO | 7 commits | audit only |
| Sprint 5 — Reporting + analytics | 🔜 PENDIENTE | — | — |
| Sprint 6 — Hardening SaaS | 🔜 PENDIENTE | — | — |

**Tests totales:** 307/307 passing (0 failed) ✅  
**Suite completa:** `docker compose exec web pytest -q`

---

## SECTOR S: Security & Tenant Foundation

**Status:** ✅ S0 | ✅ S1A | ✅ S1B | ✅ S1C | ✅ S1D (PHASE S1 COMPLETE)  
**Date Initiated:** 2026-06-19 | **Date Completed:** 2026-06-20  
**Timeline:** S0 ✅ → S1A ✅ → S1B ✅ → S1C ✅ → S1D ✅ → S2 (RLS Foundation)

### S0 Deliverables (Complete)

7 security audit documents + issue tracker infrastructure:

| Issue | Title | Status | Path |
|-------|-------|--------|------|
| **S0.1** | Tenant Inventory Audit | ✅ | `docs/security/tenant_inventory.md` |
| **S0.2** | Tenant Leak Audit | ✅ | `docs/security/tenant_leak_audit.md` |
| **S0.3** | Superuser Governance Review | ✅ | `docs/security/superuser_governance.md` |
| **S0.4** | RLS Readiness Assessment | ✅ | `docs/security/rls_readiness_report.md` |
| **S0.5** | Data Classification Audit | ✅ | `docs/security/data_classification.md` |
| **S0.6** | Security Debt Register | ✅ | `docs/security/security_debt_register.md` |
| **S0.7** | Tenant Boundary Test Plan | ✅ | `docs/security/tenant_boundary_test_plan.md` |

### S0 Key Findings

**Critical Issues (S1 Target)**:
- SD-002: Superuser escalation without X-Org-ID (4 API ViewSets leak data)
- SD-005: No RBAC enforcement (VIEWER users can write)

**Architecture Readiness**:
- ✅ 23 tenant-scoped models correctly inherit TenantModel
- ✅ TenantManager provides automatic filtering (0 raw SQL leaks found)
- ✅ RLS-ready (9 tables optimized, 14 tables need indexes)

**Phase 4B Freeze**: Effective immediately. Dashboard development paused until S1 security hardening (target unfreeze: 2026-07-15).

### S1B Deliverables (Complete)

**Unified Tenant Context Motor**:
- ✅ `contextvars` backend (async-safe, replaces threading.local)
- ✅ Robust TenantManager (auto-filters, fail-safe empty if no context)
- ✅ TenantQuerySet with context awareness
- ✅ Celery task decorator (@tenant_task) for explicit context injection
- ✅ TenantIsolationTestCase base class for cross-tenant validation
- ✅ 13 tests validating tenant boundary enforcement

**Code Changes** (5 commits):
1. contextvars backend (async-safe)
2. TenantManager auto-filtering (fail-safe)
3. Middleware + import migration
4. Celery context decorator
5. Test validation suite

### S1C Deliverables (Final Audit Complete)

**Tenant Leak Verification & Mixin Centralization Audit**:

4 Critical ViewSets Confirmed VULNERABLE:
1. **ProductViewSet** — `Product.all_objects.all()` if org=None → leaks all product data
2. **OrderViewSet** — `Order.all_objects.all()` if org=None → leaks all orders + customer data
3. **ReportViewSet** — `SalesReport.all_objects.all()` if org=None → leaks financial summaries
4. **OrderReturnViewSet** — `OrderReturn.all_objects.all()` if org=None → leaks returns + refunds

Severity Matrix: **4/4 CRITICAL**

**Mixin Centralization Analysis**:
- TenantViewMixin location: CENTRALIZED (1 class, src/interfaces/api/views.py:34-44)
- Inheritance status: ALL 4 ViewSets inherit TenantViewMixin (100%)
- Orphaned ViewSets: NONE (0/4)
- **Problem**: Leak NOT in Mixin, but DUPLICATED in each ViewSet's ternario pattern

**Global Bypass Inventory**:
- Total `.all_objects` + `.unfiltered` uses: 39
- LEAKS (unguarded): 4
- GUARDED (with filter): 29
- INTENTIONAL (test): 6
- Leak rate: 10.3% (focal problem)

**Architectural Findings**:
- ✅ TenantManager auto-filters if context set
- ✅ TenantManager returns empty if context missing
- ✅ @tenant_task decorator enforces org_id (raises ValueError)
- ✅ TenantViewMixin centralized (no duplication)
- ✅ Middleware context extraction works (X-Org-ID + slug)
- ❌ 4 ViewSets duplicate unsafe ternario pattern

### S1D Deliverables (Implementation Complete)

**Tenant Leak Remediation (Opción C Applied)**:

Code Changes:
1. ✅ TenantViewMixin.get_organization() — Enforce X-Org-ID header for superuser (raise PermissionDenied)
2. ✅ ProductViewSet.get_queryset() — Use .objects.filter(organization=org) directly
3. ✅ OrderViewSet.get_queryset() — Use .objects.filter(organization=org) directly
4. ✅ ReportViewSet.get_queryset() — Use .objects.filter(organization=org) directly
5. ✅ OrderReturnViewSet.get_queryset() — Use .objects.filter(organization=org) directly
6. ✅ Removed unreachable None-checks in create() methods

**Result**: 4 critical leaks sealed. All API queries now:
- Route through TenantManager (.objects)
- Auto-filter by organization_id from context
- Fail-safe: return empty if context missing
- Superuser: REQUIRED X-Org-ID header (else 403 PermissionDenied)

**PHASE S1 COMPLETE**: Tenant infrastructure unified, secured, and validated.

**Next Phase (S2: RLS Foundation)**:
- Implement PostgreSQL Row-Level Security policies
- Add RLS-supporting indexes
- Database-layer enforcement (cryptographic isolation)

---

## Arquitectura Actual

```
Order (PAID)
  ↓
OrderWorkflowService.handle_order_paid()
  ↓ _claim_workflow_lock() [select_for_update]
  ↓ _trigger_invoicing()
  ↓
create_invoice_task.delay(order.id)          ← Celery async
  ↓
  [Phase 1 — atomic lock]
  Order.select_for_update()
  invoice_status = 'processing', attempts += 1
  ↓
  [Phase 2 — fuera del lock]
  CreateInvoiceUseCase.execute(order)
    ↓ CompanyInvoiceConfig.objects.get(org)
    ↓ get_invoice_provider(config)            ← factory por provider_type
    ↓ provider.create_invoice(order)
      → NubefactClient (HTTP POST)            ← producción
      → MockNubefactClient                    ← desarrollo/tests
  ↓
  invoice_status = 'submitted'               ← Nubefact recibió + hash CDR
  invoice_hash = data['hash']
  ↓
  InvoiceSyncQueue.get_or_create(...)        ← idempotente, next_retry_at = now+60s
  ↓

sync_pending_invoices_task (Beat, 60s)       ← Sprint 3 Paso 3 ✅
  ↓ fan-out
sync_single_invoice_task.delay(entry_id)
  ↓
  [Phase 1 — atomic lock en InvoiceSyncQueue]
  select_for_update + idempotencia + attempts++
  ↓
  [Phase 2 — fuera del lock]
  InvoiceStatusQueryUseCase.execute(entry)
    ↓ provider.get_invoice_status(external_id)
      → NubefactClient.consultar_comprobante
      → MockNubefactClient (configurable por escenario)
  ↓
  accepted/observed/rejected → InvoiceSyncQueue.mark_completed()
  sync_pending              → schedule_next_retry() [backoff exponencial]
  finally: locked_at = None  ← siempre liberado
```

### Separación de capas (invariante)
```
Task          — orquesta, lock, retry scheduling, observabilidad
UseCase       — lógica de negocio, interpreta resultado, actualiza Order
Provider ABC  — contrato normalizado {accepted, observed, rejected, hash, ...}
HTTP Client   — único que toca requests / respuesta Nubefact cruda
```

### Estados de facturación (Order.invoice_status)

```
pending
  → queued         (en cola de emisión)
  → processing     (create_invoice_task corriendo)
  → submitted      (hash CDR recibido de Nubefact)    ← Nubefact aceptó
  → sync_pending   (en cola de polling SUNAT)
  → sync_processing (consultando SUNAT)
  → accepted       (SUNAT confirmó)                   ← ESTADO FINAL POSITIVO
  → observed       (SUNAT aceptó con observaciones)
  → rejected       (SUNAT rechazó)                    ← ESTADO FINAL NEGATIVO
  → retrying       (reintentando emisión)
  → failed         (fallo permanente)
  → cancelled      (cancelada)
```

**Distinción crítica:** `submitted ≠ accepted`
- `submitted`: Nubefact recibió el comprobante y devolvió hash CDR
- `accepted`: SUNAT procesó y confirmó el documento como válido

---

## Archivos Clave del Sistema de Facturación

### Domain
```
src/domain/
├── models/
│   ├── sales.py                     # Order: invoice_status (12 estados), invoice_hash
│   ├── config.py                    # CompanyInvoiceConfig: provider_type, token, etc.
│   ├── invoicing.py                 # InvoiceSyncQueue (MAX_ATTEMPTS=7, exhaustion, requeue)
│   ├── accounting.py                # AccountingEntry + AccountingEntryLine (SOLO accepted)
│   └── integrations.py              # ExternalServiceConfig + ExternalRequestLog
├── tasks/
│   ├── invoice_tasks.py             # create_invoice_task + _enqueue_for_sync (idempotente)
│   └── sync_invoice_tasks.py        # sync_pending + sync_single (auto-exhaustion)
├── invoice_status_ui.py             # Capa presentación: label, badge Tailwind, severity
├── templatetags/
│   └── invoice_tags.py              # Filtro |invoice_ui para templates
├── exceptions/
│   └── __init__.py                  # NubefactTemporaryError, NubefactPermanentError
└── migrations/
    ├── 0008–0011 — Sprint 1-3 base
    ├── 0012 — InvoiceSyncQueue: dead_letter + exhausted
    ├── 0013 — InvoiceSyncQueue: last_attempt_at, exhausted_at, processing_duration_ms
    ├── 0014 — AccountingEntry + AccountingEntryLine
    └── 0015 — ExternalServiceConfig + ExternalRequestLog
```

### Application
```
src/application/
├── providers/
│   ├── invoice_provider.py          # ABC: create_invoice + get_invoice_status
│   ├── nubefact_client.py           # HTTP real: POST + consultar_comprobante
│   ├── mock_nubefact_client.py      # Mock: 6 escenarios configurables
│   └── factory.py                   # get_invoice_provider(config) por provider_type
├── usecases/
│   ├── create_invoice.py            # Emisión: config → provider → persist (+ invoice_hash)
│   └── query_invoice_status.py      # Polling: provider → interpretar → actualizar Order
└── services/
    └── dashboard.py                 # OperationalDashboardService facade + 4 sub-servicios
```

### Tests
```
src/tests/
├── application/
│   ├── providers/
│   │   ├── test_nubefact_client.py      # 16 tests: HTTP codes, payload, token
│   │   └── test_get_invoice_status.py   # 17 tests: accepted/observed/rejected/pending/errors
│   └── usecases/
│       ├── test_create_invoice_usecase.py    # 7 tests
│       └── test_query_invoice_status.py     # 12 tests
└── domain/tasks/
    ├── test_invoice_tasks.py            # 10 tests: create_invoice_task
    └── test_sync_invoice_tasks.py       # 19 tests: locking, idempotencia, backoff
```

---

## InvoiceSyncQueue — Modelo de Cola

```python
class InvoiceSyncQueue(TenantModel):
    MAX_ATTEMPTS = 7           # auto-exhaustion tras 7 intentos sin resolución SUNAT
    RETRYABLE_STATUSES = frozenset({STATUS_FAILED, STATUS_EXHAUSTED, STATUS_DEAD_LETTER})

    order               = OneToOneField(Order)      # una entrada por factura
    status              = CharField(pending|processing|completed|failed|exhausted|dead_letter)
    attempts            = IntegerField(default=0)   # incrementado en Phase 1 (atómico)
    next_retry_at       = DateTimeField             # backoff: [1m,5m,15m,30m,1h,6h,24h]
    last_response       = JSONField(null=True)      # respuesta cruda de Nubefact
    last_error          = TextField(null=True)      # último mensaje de error
    locked_at           = DateTimeField(null=True)  # lock activo; null = libre
    last_attempt_at     = DateTimeField(null=True)  # timestamp del último intento
    completed_at        = DateTimeField(null=True)  # timestamp de estado terminal
    exhausted_at        = DateTimeField(null=True)  # timestamp de agotamiento
    processing_duration_ms = IntegerField(null=True)
    created_at          = DateTimeField(auto_now_add=True)

# Helpers
entry.schedule_next_retry()   # calcula next_retry_at por backoff exponencial
entry.should_exhaust()        # True si attempts >= MAX_ATTEMPTS
entry.mark_exhausted(error)   # status=exhausted, exhausted_at=now(), completed_at=now()
entry.mark_completed()        # status=completed, completed_at=now()
entry.mark_failed(error)      # status=failed, last_error, completed_at=now()
entry.requeue()               # status=pending, libera lock — solo desde RETRYABLE_STATUSES

# Índices de DB
(status, next_retry_at)       # query del fan-out
(organization, status)        # query por tenant
```

---

## Health Checks y Operabilidad

### Inspeccionar la cola en Django shell
```python
docker compose exec web python manage.py shell

from src.domain.models import InvoiceSyncQueue
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta

# Resumen de estado de la cola
InvoiceSyncQueue.all_objects.values('status').annotate(n=Count('id'))

# Pendientes por tenant
InvoiceSyncQueue.all_objects.filter(status='pending').values(
    'organization__name'
).annotate(n=Count('id')).order_by('-n')

# Facturas atascadas >24h sin resolverse (alerta operacional)
stale = InvoiceSyncQueue.all_objects.filter(
    status='pending',
    created_at__lt=timezone.now() - timedelta(hours=24)
)
print(f"Atascadas >24h: {stale.count()}")
```

### Verificar locks activos
```python
from src.domain.models import InvoiceSyncQueue
from django.utils import timezone
from datetime import timedelta

# Locks activos (algún worker procesando)
locked = InvoiceSyncQueue.all_objects.filter(locked_at__isnull=False)
for e in locked:
    age = timezone.now() - e.locked_at
    print(f"order_id={e.order_id}  tenant={e.organization_id}  age={age}  locked_at={e.locked_at}")

# Locks STALE (>10 min — worker probablemente murió)
STALE = timedelta(minutes=10)
stale_locks = InvoiceSyncQueue.all_objects.filter(
    locked_at__lt=timezone.now() - STALE
)
print(f"Locks stale: {stale_locks.count()}")

# Liberar lock stale manualmente (si el task no lo detectó automáticamente)
stale_locks.update(locked_at=None, status='pending')
```

### Verificar estado de reintentos
```python
from src.domain.models import InvoiceSyncQueue, Order

# Entradas con muchos reintentos (posible problema recurrente)
high_retries = InvoiceSyncQueue.all_objects.filter(
    status='pending', attempts__gte=4
).select_related('order').order_by('-attempts')
for e in high_retries:
    print(f"order_id={e.order_id}  attempts={e.attempts}  next={e.next_retry_at}  error={e.last_error[:80] if e.last_error else '-'}")

# Próximos en procesarse (próximos 5 minutos)
due_soon = InvoiceSyncQueue.all_objects.filter(
    status='pending',
    next_retry_at__lte=timezone.now() + timedelta(minutes=5)
)
print(f"Por procesar en <5min: {due_soon.count()}")

# Ver backlog completo de pendientes
InvoiceSyncQueue.all_objects.filter(status='pending').order_by('next_retry_at').values(
    'order_id', 'attempts', 'next_retry_at', 'last_error'
)
```

### Inspeccionar Order.invoice_status
```python
from src.domain.models import Order
from django.db.models import Count

# Distribución de estados de facturación
Order.all_objects.values('invoice_status').annotate(n=Count('id')).order_by('-n')

# Facturas en submitted sin entrar al polling (pendiente de wiring Paso 4)
Order.all_objects.filter(
    invoice_status='submitted'
).exclude(
    sync_queue_entry__isnull=False
)

# Órdenes con fallo permanente
Order.all_objects.filter(invoice_status='failed').values(
    'id', 'invoice_external_id', 'invoice_last_error', 'organization__name'
)
```

### Trigger manual de tareas
```python
# Desde Django shell
from src.domain.tasks.sync_invoice_tasks import sync_pending_invoices_task, sync_single_invoice_task

# Correr fan-out manualmente (procesa todas las pendientes ahora)
sync_pending_invoices_task.delay()

# Forzar una entrada específica por ID
sync_single_invoice_task.delay(entry_id=42)
```

### Verificar Celery desde Docker
```bash
# Ver workers activos y sus tareas
docker compose exec web celery -A config inspect active

# Ver tareas programadas en Beat
docker compose exec web celery -A config inspect scheduled

# Ver cola de tareas
docker compose exec web celery -A config inspect reserved

# Logs del Beat (ve si sync-pending-invoices dispara cada 60s)
docker compose logs celery-beat --tail=30 -f

# Logs del worker
docker compose logs celery --tail=50 -f
```

### Checklist de salud del sistema de facturación
```
[ ] Beat corriendo y disparando tasks.sync_pending_invoices cada 60s
[ ] No hay locks stale en InvoiceSyncQueue (dashboard: stale_locks == 0)
[ ] No hay facturas atascadas >24h en status=pending
[ ] No hay entries en status=processing sin locked_at (worker muerto sin finally)
[ ] Order.invoice_status='submitted' siempre tiene sync_queue_entry (wiring completo)
[ ] accepted_orders == entries_generated (dashboard: accounting consistency_ok)
[ ] Celery worker alcanzable (docker compose ps)
[ ] Redis alcanzable (broker de Celery)
```

---

## Configuración por Tenant (CompanyInvoiceConfig)

```python
# Ver config de un tenant específico
from src.domain.models import CompanyInvoiceConfig

cfg = CompanyInvoiceConfig.objects.get(organization__slug='adidas')
print(cfg.provider_type)    # 'mock' (desarrollo) | 'nubefact' (producción)
print(cfg.api_base_url)
print(cfg.endpoint_url)
# cfg.token — NO imprimir en producción

# Cambiar a producción para un tenant
cfg.provider_type = 'nubefact'
cfg.save()
```

### Activar proveedor real
Para activar `NubefactClient` en producción para un tenant:
1. `CompanyInvoiceConfig.provider_type = 'nubefact'`
2. Verificar `api_base_url` y `endpoint_url`
3. Verificar que `token` sea válido
4. Correr una prueba con una orden real en staging
5. Monitorear `invoice_status` → `submitted` → `accepted`

---

## Contratos de Respuesta

### `create_invoice` → dict
```python
{
    'status':      'submitted',    # siempre si OK (Nubefact recibió)
    'external_id': 'B001-42',      # serie-numero de Nubefact
    'hash':        'HASH-CDR-...',  # hash CDR para verificación futura
    'error':       None,
}
# Excepciones: NubefactTemporaryError | NubefactPermanentError
```

### `get_invoice_status` → dict
```python
{
    'accepted':           bool,        # SUNAT confirmó
    'observed':           bool,        # SUNAT aceptó con observaciones
    'rejected':           bool,        # SUNAT rechazó
    'hash':               str | None,  # hash CDR (prueba de recepción Nubefact)
    'provider_reference': str | None,  # enlace CDR o referencia interna
    'raw_response':       dict,        # JSON completo para auditoría
}
# Invariante: máximo uno de (accepted, observed, rejected) es True
# Si los tres son False: SUNAT sigue procesando → sync_pending
# Excepciones: NubefactTemporaryError | NubefactPermanentError
```

### Backoff exponencial (InvoiceSyncQueue)
| Intento | Delay |
|---------|-------|
| 1 | 1 minuto |
| 2 | 5 minutos |
| 3 | 15 minutos |
| 4 | 30 minutos |
| 5 | 1 hora |
| 6 | 6 horas |
| 7+ | 24 horas |

---

## Sprint 4 — Dashboard Operacional (COMPLETO)

**URL:** `/dashboard/<org_slug>/operations/`  
**Vista:** `operational_dashboard_view` — thin view, toda la lógica en `OperationalDashboardService`

### Secciones del dashboard

| Sección | Servicio | Datos |
|---------|----------|-------|
| Facturación | `InvoiceMetricsService` | counts por status, terminal_ok/err, in_flight, has_alert |
| Queue Health | `QueueHealthService` | pending, stale_locks (>10min), exhausted, dead_letter, oldest_age |
| Integraciones | `IntegrationHealthService` | por provider: total, error_rate, avg_duration, last_error |
| Contabilidad | `AccountingConsistencyService` | accepted_orders vs entries_generated, missing/orphan gaps |

### Filtro de rango temporal
`?range=1d|7d|30d|all` — pasa `date_from` a servicios de Facturación e Integraciones.

### Invariante crítico
`AccountingEntry` solo debe existir cuando `invoice_status == 'accepted'`.  
`accepted` = SUNAT confirmó (≠ `submitted` = Nubefact solo recibió).

---

## Métricas Observabilidad (placeholder — Sprint 5)

Métricas ya instrumentadas en el código (log-based, wire a Prometheus en Sprint 5):
```
invoice.poll.started       — consulta iniciada (por task_id, tenant_id, order_id, external_id)
invoice.poll.success       — estado terminal alcanzado (status=accepted|observed|rejected)
invoice.poll.retry         — SUNAT aún procesando, reagendado
invoice.poll.failed        — error permanente, sale de cola
invoice.poll.rate_limited  — placeholder para throttle por tenant (Sprint 5)
```

Formato de logs:
```
[invoice.poll.started][task_id=...][tenant_id=...][order_id=...][external_id=...][attempt=N]
[invoice.poll.success][task_id=...][tenant_id=...][order_id=...][status=accepted]
[invoice.poll.retry][task_id=...][tenant_id=...][order_id=...][next_retry_at=...][attempt=N]
```

---

## Roadmap Completo

```
✅ Sprint 1   Provider architecture + tenant config
✅ Sprint 2   Async + locking + retry + NubefactClient real
✅ Sprint 3.1 InvoiceSyncQueue model + 12 estados
✅ Sprint 3.2 get_invoice_status + InvoiceStatusQueryUseCase
✅ Sprint 3.3 sync_single + sync_pending tasks + Beat schedule
✅ Sprint 3.4 Wiring: create_invoice → InvoiceSyncQueue (idempotente, hash CDR)
✅ Mini-sprint  Operational Visibility: invoice_status_ui, admin, badges en templates
✅ Mini-sprint  Operational Recovery: MAX_ATTEMPTS=7, exhaustion, requeue admin action
✅ Mini-sprint  Accounting foundations: AccountingEntry + AccountingEntryLine
✅ Mini-sprint  Integration layer: ExternalServiceConfig + ExternalRequestLog
✅ Sprint 4   Dashboard operacional (4 secciones, filtro rango, sidebar nav)
✅ Bloque A   Analytics tests: DailyInvoiceSeriesService + DashboardKPIService (39 tests)
✅ FASE 1     Date Range UX: 6 quick filters, month nav ◀▶, ES_MONTHS, year selector
✅ FASE 2A    Drill-down: queue / integrations / accounting con tenant isolation + 22 tests
🔜 FASE 2B    Drill-down facturación: /orders/?invoice_status= desde dashboard
🔜 Sprint 5   Reporting + analytics (datos confiables ya disponibles)
🔜 Sprint 6   Hardening SaaS: rate limiting, circuit breaker, Prometheus wiring
```

---

## Comandos de Referencia Rápida

```bash
# Correr todos los tests
docker compose exec web pytest -q

# Tests de facturación solamente
docker compose exec web pytest src/tests/application/ src/tests/domain/tasks/ -v

# Con cobertura
docker compose exec web pytest --cov=src --cov-report=term-missing -q

# Aplicar migraciones
docker compose exec web python manage.py migrate

# Django shell
docker compose exec web python manage.py shell

# Ver logs de Celery en tiempo real
docker compose logs celery -f
docker compose logs celery-beat -f

# Flower (monitoreo de tareas)
# http://localhost:5555

# Tests drill-down operacional
docker compose exec web pytest src/tests/interfaces/web/test_drill_down_views.py -v

# Tests analytics
docker compose exec web pytest src/tests/application/services/ -v
```

---

## Dashboard Operacional — FASE 1 + FASE 2A (COMPLETO)

### Rutas operacionales

```
/dashboard/<slug>/operations/              → Dashboard principal
/dashboard/<slug>/operations/queue/        → Cola SUNAT (drill-down)
/dashboard/<slug>/operations/integrations/ → Logs externos (drill-down)
/dashboard/<slug>/operations/accounting/   → Contabilidad (drill-down)
```

### Vistas nuevas (FASE 2A — commit `99b52c3`)

| Vista | Filtros |
|-------|---------|
| `queue_detail_view` | `?status=pending\|failed\|exhausted\|dead_letter\|stale` |
| `integration_logs_view` | `?provider=<name>&status=error` |
| `accounting_detail_view` | `?filter=missing_entries\|orphan_entries` |

- `stale` = virtual: `locked_at < now - 10min` (no es status real en DB)
- `accounting_detail_view` usa `show_mode='orders'|'entries'` para alternar tabla

### Servicios analytics (Bloque A — commit `4fc016a`)

| Servicio | Archivo |
|----------|---------|
| `DailyInvoiceSeriesService` | `src/application/services/dashboard.py` |
| `DashboardKPIService` | `src/application/services/dashboard.py` |
| `DateRangeService` | `src/domain/services/date_range_service.py` |

`ES_MONTHS` dict en `date_range_service.py` — labels español sin locale del sistema.

### Date Range UX (FASE 1 — commit `7ad0d82`)

Quick filters: `?period=day|week|month|30d|year|all`  
Navegación mensual: `?period=month&month=5&year=2026`

---

## Bug conocido (documentado, no bloqueante)

**Timezone inconsistency en `DailyInvoiceSeriesService`:**
- `TruncDate` usa `TIME_ZONE=America/Lima` para truncar fechas
- `timezone.now().date()` devuelve fecha UTC
- Órdenes cerca de medianoche Lima (UTC-5) pueden caer en día incorrecto
- Fix futuro: usar `timezone.localdate()` en lugar de `now.date()`

---

## Próximos pasos

1. **FASE 2B** — Drill-down de facturación:
   - Link "3 rechazadas" → `/orders/?invoice_status=rejected`
   - Agregar filtro `?invoice_status=` a `order_list_view`
   - 2 tests mínimos
2. **FASE 3** — Logs con payload viewer (sin exponer secretos/tokens)
3. **Timezone fix** — `DailyInvoiceSeriesService` usar `timezone.localdate()`

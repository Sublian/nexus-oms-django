# Nexus OMS — Resumen de Avances del Proyecto
**Fecha de corte:** 17 de Mayo, 2026 | **Versión:** 3.1.0-WIP | **Fase:** Sprint 3 en progreso

---

## Estado General

| Sprint | Estado | Commits | Tests |
|--------|--------|---------|-------|
| Sprint 1 — Provider architecture + tenant config | ✅ COMPLETO | `3197ec9` | +7 |
| Sprint 2 — Async + locking + retry + NubefactClient | ✅ COMPLETO | `55cebbd`→`d061c77` | +48 |
| Sprint 3 Paso 1 — InvoiceSyncQueue + estados expandidos | ✅ COMPLETO | `1f9878f` | — |
| Sprint 3 Paso 2 — get_invoice_status + UseCase | ✅ COMPLETO | `2752990` | +29 |
| Sprint 3 Paso 3 — Tasks de polling + Beat schedule | ✅ COMPLETO | `906f9ed` | +19 |
| Sprint 3 Paso 4 — Wiring: create_invoice → InvoiceSyncQueue | 🔜 PENDIENTE | — | — |
| Sprint 4 — Dashboard operacional + retries manuales | 🔜 PENDIENTE | — | — |
| Sprint 5 — Reporting + analytics | 🔜 PENDIENTE | — | — |

**Tests totales:** 159 / 159 passing  
**Suite completa:** `docker compose exec web pytest -q`

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
  InvoiceSyncQueue.create(...)               ← PENDIENTE: Paso 4 de Sprint 3
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
│   └── invoicing.py                 # InvoiceSyncQueue (TenantModel, lockable, retryable)
├── tasks/
│   ├── invoice_tasks.py             # create_invoice_task (emisión async)
│   └── sync_invoice_tasks.py        # sync_pending_invoices_task + sync_single_invoice_task
├── exceptions/
│   └── __init__.py                  # NubefactTemporaryError, NubefactPermanentError
└── migrations/
    ├── 0008 — CompanyInvoiceConfig + Order invoice fields
    ├── 0009 — invoice_attempts, invoice_last_error, status choices
    ├── 0010 — CompanyInvoiceConfig.provider_type
    └── 0011 — InvoiceSyncQueue + 12 estados en invoice_status
```

### Application
```
src/application/
├── providers/
│   ├── invoice_provider.py          # ABC: create_invoice + get_invoice_status
│   ├── nubefact_client.py           # HTTP real: POST + consultar_comprobante
│   ├── mock_nubefact_client.py      # Mock: 6 escenarios configurables
│   └── factory.py                   # get_invoice_provider(config) por provider_type
└── usecases/
    ├── create_invoice.py            # Emisión: config → provider → persist
    └── query_invoice_status.py      # Polling: provider → interpretar → actualizar Order
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
    order         = OneToOneField(Order)       # una entrada por factura
    status        = CharField(pending|processing|completed|failed)
    attempts      = IntegerField(default=0)    # incrementado en Phase 1 (atómico)
    next_retry_at = DateTimeField             # backoff: [1m,5m,15m,30m,1h,6h,24h]
    last_response = JSONField(null=True)      # respuesta cruda de Nubefact
    last_error    = TextField(null=True)      # último mensaje de error
    locked_at     = DateTimeField(null=True)  # lock activo; null = libre
    completed_at  = DateTimeField(null=True)  # timestamp de estado terminal
    created_at    = DateTimeField(auto_now_add=True)

# Helpers
entry.schedule_next_retry()   # calcula next_retry_at por backoff exponencial
entry.mark_completed()        # status=completed, completed_at=now()
entry.mark_failed(error)      # status=failed, last_error, completed_at=now()
entry.release_lock()          # locked_at=None (model-level; task usa .update())

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
[ ] No hay locks stale en InvoiceSyncQueue
[ ] No hay facturas atascadas >24h en status=pending
[ ] No hay entries en status=processing sin locked_at (worker muerto sin finally)
[ ] Order.invoice_status='submitted' con sync_queue_entry creada (Paso 4 pendiente)
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
    'status':      'issued',       # siempre si OK
    'external_id': 'B001-42',      # serie-numero de Nubefact
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

## Pendiente — Sprint 3 Paso 4 (Próxima sesión)

**Objetivo:** Conectar `create_invoice_task` con `InvoiceSyncQueue`.

Cuando `create_invoice_task` recibe respuesta exitosa de Nubefact:
1. Cambiar `invoice_status` de `issued` → `submitted`
2. Guardar `invoice_hash` si viene en la respuesta
3. Crear `InvoiceSyncQueue` entry con `next_retry_at = now() + 60s`

Archivos a modificar:
- `src/domain/tasks/invoice_tasks.py` — Phase 2: crear entry en InvoiceSyncQueue
- `src/application/usecases/create_invoice.py` — retornar hash si disponible
- `src/application/providers/nubefact_client.py` — incluir hash en respuesta de `create_invoice`
- Tests de regresión: `test_invoice_tasks.py` espera `invoice_status='issued'` → actualizar a `submitted`

---

## Pendiente — Sprint 4: Dashboard Operacional

Basado en guia6.md:
- Vista por tenant: emitidas, pendientes, rechazadas, retrying
- Botón "Reprocesar factura" (re-enqueue en InvoiceSyncQueue)
- Admin UI para InvoiceSyncQueue con filtros: tenant, status, retries, aging
- Alertas: facturas pending > 30 min → notificación operacional

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
🔜 Sprint 3.4 Wiring: create_invoice → InvoiceSyncQueue (PRÓXIMO)
🔜 Sprint 4   Dashboard operacional + retries manuales
🔜 Sprint 5   Reporting + analytics (datos confiables ya disponibles)
🔜 Sprint 6   Hardening SaaS: rate limiting, circuit breaker, dead letter queue
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
```

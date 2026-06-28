# Infrastructure Root — Nexus OMS Persistence & Async

## ¿Qué es?

Capa de infraestructura: persistencia (PostgreSQL), orquestación asíncrona (Celery + Redis), y servicios externos.

## Persistencia (PostgreSQL)

### Configuración
- **Driver**: psycopg3 3.3.3 (Python 3.11+ async support)
- **Pool**: Django ORM + psycopg3 built-in connection pooling
- **Transactions**: SERIALIZABLE isolation level en críticas
- **Migrations**: Django migration framework

### Modelos Heredables

**TenantModel** (abstract):
```python
class TenantModel(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    
    class Meta:
        abstract = True
    
    objects = TenantManager()  # Filtra por tenant activo
    all_objects = models.Manager()  # Bypass (solo admin/migration/tests)
```

**Todos los modelos de negocio heredan de TenantModel**:
- Order, OrderItem, OrderReturn
- Invoice, InvoiceSyncQueue, AccountingEntry
- Stock, StockMovement
- PurchaseOrder, PurchaseOrderItem
- ExchangeRate, CompanyInvoiceConfig

### TenantManager (Filtrado Automático)

```python
class TenantManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset()
        org_id = get_current_organization()  # thread-local
        if org_id:
            return qs.filter(organization_id=org_id)
        return qs  # Fallback: queryset vacío si no hay contexto
```

**Invariante**: NUNCA usar `.all_objects` en código de negocio (solo admin, migrations, tests).

### Thread-Local Context

**Archivo**: `src/infrastructure/multitenancy/thread_local.py`

```python
_organization_id = threading.local()

def set_current_organization(org_id):
    _organization_id.value = org_id

def get_current_organization():
    return getattr(_organization_id, 'value', None)

def clear_current_organization():
    if hasattr(_organization_id, 'value'):
        del _organization_id.value
```

**Ciclo de vida**:
1. Middleware entrada: `set_current_organization(org_id)`
2. Views ejecutan: `TenantManager` filtra automáticamente
3. Middleware salida: `clear_current_organization()` (CRÍTICO)

---

## Async Orchestration (Celery + Redis)

### Celery Configuration

**Broker**: Redis (same instance as cache)
**Result Backend**: Redis
**Serializer**: JSON (not pickle, for security)

### Beat Schedule (3 Jobs)

**Archivo**: `config/settings/base.py → CELERY_BEAT_SCHEDULE`

```python
CELERY_BEAT_SCHEDULE = {
    'generate-weekly-reports': {
        'task': 'generate_weekly_all_orgs',
        'schedule': crontab(hour=0, minute=0, day_of_week=1),  # Mon 00:00 UTC
    },
    'sync-exchange-6am': {
        'task': 'sync_daily_exchange_rate',
        'schedule': crontab(hour=6, minute=0),  # Daily 06:00 UTC
    },
    'sync-pending-invoices': {
        'task': 'sync_pending_invoices_task',
        'schedule': 60,  # Every 60 seconds (CRÍTICO)
    },
}
```

### Task Inventory

| Task | Trigger | Criticidad |
|------|---------|-----------|
| `create_invoice_task` | Order → PAID | Alta |
| `sync_pending_invoices_task` | Beat c/60s | Alta |
| `sync_single_invoice_task` | Fan-out por queue entry | Alta |
| `generate_weekly_all_orgs` | Beat lunes 00:00 | Media |
| `sync_daily_exchange_rate` | Beat diariamente 06:00 | Media |

### Test Mode

**Archivo**: `config/settings/testing.py`

```python
CELERY_TASK_ALWAYS_EAGER = True  # Sincronously execute tasks
```

**Implicaciones**:
- `task.delay()` = `task()` (sin Redis)
- Transacciones DB reales (no mock)
- No cubre serialización de argumentos
- No cubre comportamiento real de cola (latency, timeouts)

---

## External Services

### APIMigo Client
- **URL**: https://api.apimigo.pe (mock en tests)
- **Endpoints**: Exchange rate, Payment processing
- **Auth**: API key por tenant en `CompanyInvoiceConfig`
- **Fallback**: Hardcoded rate si APIMigo falla

### Nubefact Client (Invoice Provider)
- **URL**: https://api.nubefact.com
- **Endpoints**: Create invoice, Query status
- **Auth**: API key por tenant
- **Error Taxonomy**: PermanentError (400/401/403/422) vs TemporaryError (5xx)

### Provider Abstraction

**Interfaz**: `InvoiceProvider` (ABC)
- Implementación: `NubefactClient` (producción)
- Mock: `MockNubefactClient` (tests/desarrollo)
- Selección: `CompanyInvoiceConfig.provider_type`

---

## Backup & Recovery

**No implementado aún**. Próximo tema S2.X:
- [ ] Backup automático PostgreSQL (pg_dump c/día)
- [ ] WAL archiving para PITR
- [ ] Hot standby replica (HA)

---

## Monitoreo (Observability)

**Logging**:
- Django logging + structlog (JSON format)
- Celery task logs → Redis + file

**Métricas**:
- Application health (task queue depth, latency)
- Database (connections, slow queries)
- Redis (memory usage, key count)

**Alertas**:
- Beat job failure
- Invoice sync queue exhausted
- PostgreSQL connection pool exhausted

---

## ¿Por qué esta arquitectura?

1. **PostgreSQL**: ACID guarantees para datos financieros críticos
2. **Celery**: Async offload de invoicing (I/O bound)
3. **Redis**: Broker rápido + caching
4. **Thread-local**: Multi-tenant context sin pasar parámetro a todo
5. **TenantManager**: Filtrado automático reduce riesgo de data leak

---

## Relaciones

- [Architecture](../architecture/root.md) — Cómo estas piezas se conectan
- [Domain](../domain/root.md) — Lógica que ejecuta infraestructura
- [Security](../security/root.md) — Protecciones en nivel DB (S2.X)

---

**Estado**: STABLE (producción)
**Última actualización**: 2026-06-27
**Responsable**: Tech Lead
**Siguiente nodo recomendado**: [security/root.md](../security/root.md)

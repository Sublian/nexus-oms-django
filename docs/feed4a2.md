# 🧭 FASE 4A: Observability Foundation — Snapshot Oficial (Domingo 2026-06-14)

## STATUS: ✅ 100% COMPLETADO

---

## 📊 PASO 0: Reparación del Seeder (Completado)

**Commit:** `6ec1182` — "fix: cast order_shipping to Decimal in seed_data command"

- Líneas 220, 269, 273 en `src/domain/management/commands/seed_data.py`
- Cast explícito: `shipping_fee = Decimal(str(org.default_shipping_fee))`
- Cuantización en totales: `.quantize(Decimal('0.01'))`
- Validación: `docker-compose exec web python manage.py seed_data --orders 100` ✓

---

## 🔍 PASO 1.0: Verificación Física del Modelo ExternalRequestLog

### Hallazgos Exactos de Tipos de Datos:

```
ExternalRequestLog.order          → ForeignKey('domain.Order')
  DB column: order_id             → BigInteger (nullable=True)
  
ExternalRequestLog.organization   → ForeignKey('domain.Organization') [heredado TenantModel]
  DB column: organization_id      → Integer (nullable=False)
  
ExternalRequestLog.service        → ForeignKey(ExternalServiceConfig)
  DB column: service_id           → BigInteger (nullable=True)
  
ExternalRequestLog.provider_name  → CharField max_length=50
ExternalRequestLog.operation      → CharField max_length=100
ExternalRequestLog.status_code    → IntegerField (nullable=True)
ExternalRequestLog.duration_ms    → IntegerField (nullable=True) ← medido en milisegundos
ExternalRequestLog.success        → BooleanField (nullable=True)
ExternalRequestLog.error_message  → TextField (nullable=True) ← prefijo [CATEGORY] aquí
ExternalRequestLog.request_payload → JSONField (nullable=True)
ExternalRequestLog.response_payload → JSONField (nullable=True)
ExternalRequestLog.created_at     → DateTimeField (auto_now_add=True)

Order.id                          → BigAutoField (PK)
```

**Confirmación:** Todos los tipos nativos respetados. Sin colisiones de conversión.

---

## 🔍 PASO 1.1: Evidencia de InvoiceStatusQueryUseCase.execute()

### Línea 27 — Contexto Disponible:

```python
def execute(self, sync_entry) -> dict:
    order = sync_entry.order  # ← LÍNEA 27: order COMPLETO disponible en scope

    if not order.invoice_external_id:
        raise NubefactPermanentError(...)

    # ... resolución de config ...

    result = provider.get_invoice_status(order, order.invoice_external_id)  # ← LÍNEA 46: ACTUALIZADA
    # Antes: get_invoice_status(order.invoice_external_id)
    # Ahora: get_invoice_status(order, order.invoice_external_id)
```

**Acceso disponible en scope local:**
- ✅ `order` (objeto completo, OneToOneFK en InvoiceSyncQueue)
- ✅ `order.id` (PK BigAutoField)
- ✅ `order.organization_id` (heredado TenantModel)
- ✅ `order.invoice_external_id` (string ej: 'B001-123')
- ✅ `order.organization` (FK a Organization)

**Conclusión:** ESCENARIO A confirmado. Contexto completo disponible → cambio de firma justificado.

---

## 🏛️ PASO 1.1.C: InvoiceSyncQueue — Correlación en Cola

### Campos Físicos Confirmados:

```
InvoiceSyncQueue.order            → OneToOneField('domain.Order', on_delete=CASCADE)
  DB column: order_id             → BigInteger

InvoiceSyncQueue.organization     → ForeignKey('domain.Organization') [TenantModel]
  DB column: organization_id      → Integer

InvoiceSyncQueue.status           → CharField (pending, processing, completed, failed, exhausted, dead_letter)
InvoiceSyncQueue.attempts         → IntegerField
InvoiceSyncQueue.next_retry_at    → DateTimeField
InvoiceSyncQueue.last_response    → JSONField (nullable)
InvoiceSyncQueue.last_error       → TextField (nullable)
InvoiceSyncQueue.locked_at        → DateTimeField (nullable) [lock distribuido]
InvoiceSyncQueue.last_attempt_at  → DateTimeField (nullable)
InvoiceSyncQueue.completed_at     → DateTimeField (nullable)
InvoiceSyncQueue.exhausted_at     → DateTimeField (nullable)
InvoiceSyncQueue.processing_duration_ms → IntegerField (nullable) [placeholder Sprint 5]
```

**Información NO desnormalizada en cola:**
- ❌ `invoice_external_id` → vive en `Order.invoice_external_id`

**Decisión:** Pasar `order` a `get_invoice_status()` → acceso directo al external_id dentro del cliente HTTP.

---

## 🚀 PASO 1.2: Implementación — Entregables A, B, C

### ✅ ENTREGABLE A: Instrumentación de ExternalRequestLog

**Archivo:** `src/application/providers/nubefact_client.py`

**Método create_invoice(order):**
- Captura `time.time()` antes de `requests.post()`
- Calcula `duration_ms = int((time.time() - start_time) * 1000)`
- Crea `ExternalRequestLog` en punto único de salida: `_log_external_request()`

**Método get_invoice_status(order, external_id):**
- Nueva firma: parámetro `order` agregado
- Misma instrumentación: tiempo + log + categoría
- Anti-duplicación: logging SOLO en cliente

**Helper _log_external_request():**
```python
def _log_external_request(self, order, operation, request_payload, 
                         response_payload, status_code, duration_ms,
                         success, error_message=None):
    ExternalRequestLog.objects.create(
        organization=order.organization,
        service=None,  # nullable, sin contexto ExternalServiceConfig
        provider_name='nubefact',
        operation=operation,  # 'create_invoice' | 'query_status'
        order=order,
        request_payload=request_payload,
        response_payload=response_payload,
        status_code=status_code,
        duration_ms=duration_ms,  # milisegundos capturados
        success=success,
        error_message=error_message,  # con prefijo [CATEGORY]
    )
```

### ✅ ENTREGABLE B: Taxonomía de Errores Dinámica

**Archivo nuevo:** `src/domain/observability.py`

```python
class ErrorCategory(str, Enum):
    TEMPORARY = "TEMPORARY"      # Timeout, 502, 503, 504 — reintentable
    PERMANENT = "PERMANENT"      # 400, 401, 403, 422 — no reintentar
    AUTH = "AUTH"                # 401, 403
    VALIDATION = "VALIDATION"    # 422
    RATE_LIMIT = "RATE_LIMIT"   # 429

def classify_error(exception_or_status_code) -> ErrorCategory:
    # Traduce dinámicamente HTTP codes + excepciones → categoría
```

**Integración:** Prefijo en `error_message`:
```
"[TEMPORARY] Timeout after 15s — order_id=..."
"[PERMANENT] HTTP 400 — order_id=..."
"[AUTH] HTTP 401 — order_id=..."
```

**Persistencia:** Texto embebido en `ExternalRequestLog.error_message` (sin nueva columna DB).

### ✅ ENTREGABLE C: QA y Tests

**Archivo:** `src/tests/application/providers/test_observability_logs.py`

**18 Tests Nuevos:**
- 11 TestClassifyError — cobertura de codes HTTP + excepciones
- 7 TestExternalRequestLogCreation — verificación de log + duration_ms + categoría

**Coverage:**
- ✅ Log creado en request exitoso (success=True)
- ✅ Log creado en errores HTTP (400, 503, timeout)
- ✅ Prefijo de categoría en error_message
- ✅ duration_ms capturado (time.time())
- ✅ Anti-duplicación: 1 HTTP request = 1 log exacto
- ✅ Tipos nativos respetados

---

## 🔄 Cambios de Firma — 4 Archivos Periféricos

| Archivo | Cambio | Status |
|---------|--------|--------|
| `InvoiceProvider` (interface) | `get_invoice_status(order, external_id)` | ✅ |
| `NubefactClient` | `get_invoice_status(order, external_id)` | ✅ |
| `MockNubefactClient` | `get_invoice_status(order, external_id)` | ✅ |
| `InvoiceStatusQueryUseCase` | Línea 46: pasar `order` al provider | ✅ |

**Impacto:** Mínimo. Callsites bajo control, sin dependencias externas.

---

## 💾 Git Commits — Política de Coherencia

| # | Mensaje | Hash | Status |
|---|---------|------|--------|
| 1 | `fix: cast order_shipping to Decimal in seed_data command` | 6ec1182 | ✅ |
| 2 | `feat: instrument external request log for nubefact client` | 8027601 | ✅ |
| 3 | `test: add unit tests for observability logs and taxonomy` | 8598038 | ✅ |
| 4 | `docs: phase 4a observability foundation completion report` | 4eb35e6 | ✅ |
| 5 | `fix: adapt existing tests to get_invoice_status signature change` | 41f9098 | ✅ |
| 6 | `cleanup: remove temporary check_models.py script` | 0280aef | ✅ |

---

## 🧪 Baseline de Tests

### Antes de FASE 4A:
```
307 passed (0 failed, 0 errors)
```

### Después de FASE 4A:
```
325 passed (307 original + 18 nuevos observabilidad)
0 failed | 0 errors
```

**Validación:** `docker-compose exec web pytest -q`  
**Resultado:** 325 passed in 64.42s

---

## 🚫 Restricciones Inmutables — Status

✅ NO UI/HTML/HTMX/templates modificados  
✅ NO archivos de migración generados  
✅ NO esquema PostgreSQL alterado  
✅ Logging ÚNICAMENTE en cliente HTTP (antiduplicación)  
✅ Tipos nativos ExternalRequestLog respetados exactamente  
✅ Multi-tenancy: organization_id correctamente asociada  

---

## 📝 Deuda Técnica Transitoria — Aceptada

**Decisión arquitectónica transitoria:**
- Prefijo de categoría en texto de `error_message` en lugar de columna separada
- **Razón:** Evitar migraciones en Sprint 4A
- **Validez:** Hasta Sprint 5/6 cuando se normalice a columna `error_category`
- **Marcaje:** Línea 14 de este documento (bitácora de decisión técnica)

---

## 🎯 Qué Queda Para Mañana Lunes (FASE 5)

### Sprint 5: Métricas Exportables
- [ ] Endpoints para exportar logs a Prometheus/StatsD
- [ ] Alertas sobre tasas de error por tenant
- [ ] Dashboard de observabilidad en Web UI

### Sprint 6: Normalización
- [ ] Migración: columna `error_category` en ExternalRequestLog
- [ ] Índices adicionales para queries de observabilidad
- [ ] Archivado de logs antiguos

---

## 📌 Cómo Retomar Mañana (Checklist)

**Mañana lunes 2026-06-15 al iniciar:**

1. Leer este snapshot (feed4a2.md)
2. Revisar `git log --oneline` últimos 6 commits
3. Correr `docker-compose exec web pytest -q` para validar baseline (325)
4. Verificar que `ExternalRequestLog` en admin Django muestra logs con duración
5. Revisar `resume.md` — debe mostrar FASE 4A: ✅ 100% COMPLETADA

---

## Firmado

**Jornada:** Domingo 2026-06-14  
**Ingeniero:** Luis Gonzalez (lagonzalez@fiberlux.pe)  
**Estado:** 🟢 FASE 4A CERRADA — Listo para Sprint 5  
**Próxima revisión:** Lunes 2026-06-15 09:00 UTC

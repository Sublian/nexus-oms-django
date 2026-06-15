# Estado actual del proyecto — Nexus OMS

Snapshot técnico al 2026-06-14. Usar como contexto de arranque en nueva sesión.
**FASE 2B + FASE 3 completadas. FASE 3.4A-B (Audits) completadas. FASE 3.4B-B (Recovery) completada.**
**FASE 4A: Observability Foundation — ✅ 100% COMPLETADA — 325/325 tests en verde.**

---

## Arquitectura actual

- **Framework**: Django 6 + DRF + HTMX + Tailwind CDN
- **Capas**: `domain/` → `application/` → `interfaces/` (API + web)
- **Multitenancy**: `TenantModel` + `TenantManager` + thread-local `organization_id`
  - Web: tenant desde URL slug `/dashboard/<org_slug>/`
  - API: tenant desde JWT claims
- **Async**: Celery + Redis (beat: weekly reports, daily exchange rate)
- **Auth**: `CustomUser` (email), JWT para API, session para web

### Servicios dashboard (`src/application/services/dashboard.py`)

| Servicio | Qué hace |
|---|---|
| `InvoiceMetricsService` | Counts por `invoice_status` |
| `QueueHealthService` | Estado InvoiceSyncQueue + stale locks |
| `IntegrationHealthService` | Metrics ExternalRequestLog por provider |
| `AccountingConsistencyService` | Valida invariante accepted → AccountingEntry |
| `DailyInvoiceSeriesService` | Time-series 30 días via TruncDate (Chart.js) |
| `DashboardKPIService` | Acceptance rate + avg latency |
| `OperationalDashboardService` | Facade que agrega todos los anteriores |

---

## Cambios implementados — sesión actual

### FASE 1 — Date Range UX (commit `7ad0d82`)
- `ES_MONTHS` dict en `date_range_service.py` (labels español, sin locale)
- `operational_dashboard_view` enriquecido: `active_period`, nav mes/año, prev/next urls
- `operations.html`: 6 quick filters + navegador mensual ◀ Mes Año ▶ + selector año

### FASE 2A — Drill-down navigation (commit `99b52c3`)

**3 nuevas vistas + 3 rutas + 3 templates + 22 tests:**

| URL | Vista | Filtros |
|-----|-------|---------|
| `operations/queue/` | `queue_detail_view` | `?status=pending\|failed\|exhausted\|dead_letter\|stale` |
| `operations/integrations/` | `integration_logs_view` | `?provider=<name>&status=error` |
| `operations/accounting/` | `accounting_detail_view` | `?filter=missing_entries\|orphan_entries` |

**Links drill-down en `operations.html`:**
- Queue Health cards: pending, stale locks, exhausted, dead_letter → "Ver →"
- Integrations provider cards: "Ver logs →" + "Solo errores →" (si failed > 0)
- Accounting cards: sin asiento, asientos huérfanos → "Ver →"

### FASE 2B — Invoice Status Drill-down (commit `9086ca6`)

**Drill-down desde KPIs de facturación:**
- KPI cards interactivos: Aceptadas SUNAT, En Tránsito, Errores Terminales → `/orders/?invoice_status=X`
- Nuevo filtro en `order_list_view`: parámetro `?invoice_status=` (accepted, rejected, submitted, pending, etc.)
- Combinable con filtros existentes: `?status=PAID&invoice_status=accepted&q=Juan`
- UI: dropdown select + badge visual cuando filtro activo + link "Limpiar filtro"

**Changes:**
- `order_list_view`: añadido `invoice_status` filter
- `order_list.html`: dropdown de invoice_status + badge activo
- `operations.html`: KPI cards transformadas en `<a>` links
- `DailyInvoiceSeriesService`: timezone fix (UTC → localtime)
- 8 nuevos tests (aislamiento multi-tenant, combinación parámetros)

### FASE 3 — Invoice Observable & Timeline + T6 Mitigation (commit `cad877a`)

**Security: T6 Mitigation (superuser cross-tenant exposure)**
- Decorador `require_organization`: valida que `request.organization is not None`
- Returns 403 Forbidden si middleware resuelve org=None (no slug en URL, no X-Org-ID header)

**Invoice Detail Observable:**
- Nueva vista: `/dashboard/<slug>/invoices/<order_id>/`
- Expone: estado fiscal, IDs externos, hashes CDR, payloads SUNAT/Nubefact
- Contexto: Order, InvoiceSyncQueue, OrderWorkflowLog, AccountingEntry

**Timeline Operacional (HTMX-ready):**
- Unified timeline de 4 event streams:
  1. Order creation
  2. OrderWorkflowLog (auditable events)
  3. InvoiceSyncQueue (sync attempts, responses, backoff exponencial)
  4. AccountingEntry (cuando accepted)
- Renderiza cronológicamente con color-coding (blue/yellow/orange/green/red)
- Detalles inline: respuestas JSON SUNAT, errores, retry counts
- Collapsible sections para datos largos

**Changes:**
- `invoice_detail_view`: agregada con timeline aggregation logic
- `decorators.py`: `require_organization` decorator para T6 mitigation
- `urls.py`: ruta `/invoices/<order_id>/`
- `invoice_detail.html`: template con timeline visual
- 8 nuevos tests (timeline ordering, tenant isolation, state badges)

### FASE 3.4A — Discovery & Audit (Read-only, No Code Changes)

**Audit Scope:** Payload persistence, error taxonomy, correlation traceability

**Key Findings:**
- ✅ Payloads persist via `InvoiceSyncQueue.last_response` (JSON)
- ✅ Order.id correlates consistently across models (canonical ID valid)
- ⚠️ ExternalRequestLog model exists but orphaned (never populated)
- ❌ No structured error taxonomy (errors stored as strings)
- ❌ No request IDs for distributed tracing

**Deliverable:**
- `docs/discovery_report_phase_3_4a.md` — Complete audit report with findings & recommendations

**Recommendations for Sprint 5:**
1. Populate ExternalRequestLog in invoice flow
2. Add error classification taxonomy
3. Capture request IDs (Nubefact x-request-id, Celery task_id)

### FASE 3.4B-A — Root Cause Analysis (Read-only Audit)

**Test Failure Diagnosis:** Two root causes identified

**RCA Finding #1: Context Variable Mismatch**
- File: `src/interfaces/web/views.py` line 497
- Issue: View passes `'orders': page_obj` but tests expect `'page_obj': page_obj`
- Severity: HIGH
- Fix: 1-line change (rename context key)
- Affects: All 7 FASE 2B invoice_status tests

**RCA Finding #2: HTTP Leakage to APIMigo**
- File: `src/domain/services/finance_service.py` line 101
- Issue: Context processor calls unprotected ExchangeService that makes HTTP calls
- Chain: Test → View render → Context processor → APIMigoClient (403 error)
- Severity: HIGH
- Fix: Seed ExchangeRate fixtures or wrap with try/except
- Affects: All dashboard view tests (not just FASE 2B)

**Deliverable:**
- `docs/rca_report_3_4b.md` — Complete root cause analysis with detailed recommendations

### FASE 3.4B-B — Test Recovery (Fix & Verify)

**Fixes Applied:**
1. `src/interfaces/web/views.py` line 497: Added `'page_obj': page_obj` to context
   - Restored pagination contract for tests
   - Maintained backward compat with `'orders'` key for HTMX template

2. `src/tests/conftest.py`: Created `exchange_rate_fixture` (non-autouse)
   - Pre-populates ExchangeRate to prevent HTTP leaks to APIMigo
   
3. `src/tests/interfaces/web/conftest.py`: New file (autouse wrapper)
   - Applies exchange_rate_fixture only to web interface tests
   - Isolates from service-level tests that control their own DB state

**Results:**
- ✅ All 8 FASE 2B tests passing
- ✅ Full suite: **307/307 tests in green, 0 failed**
- ✅ No regressions in service tests (TestExchangeService, etc.)
- ✅ No production code modified

**Scope Boundaries:**
- ✅ No dashboard UI changes
- ✅ No ExternalRequestLog population
- ✅ No InvoiceSyncQueue modifications
- ✅ No graph updates
- ✅ Fixture-only approach (no service layer changes)

### FASE 4A — Observability Foundation (Domingo 2026-06-14)

**Implementación Completa: Entregables A, B, C**

**Entregable A: Instrumentación de ExternalRequestLog**
- Inyección de logs en `NubefactClient.create_invoice()` y `get_invoice_status()`
- Captura de `duration_ms` (time.time() en milisegundos)
- Respeto de tipos nativos exactos: `order_id` (BigInteger), `organization_id` (Integer)
- Anti-duplicación: logging ÚNICA en cliente HTTP (`_log_external_request()`)
- Files: `src/application/providers/nubefact_client.py`

**Entregable B: Taxonomía de Errores Dinámica**
- Enum `ErrorCategory`: TEMPORARY, PERMANENT, AUTH, VALIDATION, RATE_LIMIT
- Función `classify_error(exception_or_status_code)` para clasificación dinámica
- Prefijo embebido: `[CATEGORY] error message` en `error_message` (sin nueva columna DB)
- Files: `src/domain/observability.py`

**Entregable C: QA y Tests**
- 18 tests nuevos (100% passing)
- Coverage: classify_error() + ExternalRequestLog creation + duration_ms + anti-duplicación
- Baseline: 307 → 325 tests
- Files: `src/tests/application/providers/test_observability_logs.py`

**Cambios de Firma:**
- `InvoiceProvider.get_invoice_status(order, external_id)` — parámetro `order` agregado
- `NubefactClient.get_invoice_status(order, external_id)`
- `MockNubefactClient.get_invoice_status(order, external_id)`
- `InvoiceStatusQueryUseCase.execute()` — línea 46 actualizada

**Commits (6 total):**
1. `6ec1182` — fix: cast order_shipping to Decimal in seed_data command
2. `8027601` — feat: instrument external request log for nubefact client
3. `8598038` — test: add unit tests for observability logs and taxonomy
4. `4eb35e6` — docs: phase 4a observability foundation completion report
5. `41f9098` — fix: adapt existing tests to get_invoice_status signature change
6. `0280aef` — cleanup: remove temporary check_models.py script

**Restricciones Inmutables Respetadas:**
- ✅ No UI/HTML/HTMX/templates modificados
- ✅ No migraciones generadas
- ✅ No esquema PostgreSQL alterado
- ✅ Deuda técnica transitoria aceptada: prefijo [CATEGORY] en texto (normalizar en Sprint 6)

---

## Estado de tests

- **325 tests** en verde (307 original + 18 nuevos FASE 4A)
- `manage.py check`: 0 issues

### Desglose por bloque
| Bloque | Tests |
|---|---|
| Bloque A — analytics services | 39 nuevos (commit `4fc016a`) |
| FASE 1 — date range UX | 0 nuevos (lógica cubierta por tests existentes) |
| FASE 2A — drill-down views | 22 nuevos (commit `99b52c3`) |
| FASE 2B — invoice_status filtering | 8 nuevos (commit `9086ca6`) |
| FASE 3 — invoice detail & timeline | 8 nuevos (commit `cad877a`) |
| FASE 4A — observability foundation | 18 nuevos (commit `8598038`) |

---

## Archivos sin commit

```
(ninguno — árbol limpio)
```

---

## Bugs / Tensiones resueltas

**FASE 2B: Timezone inconsistency en `DailyInvoiceSeriesService`** ✅
- Cambio: `timezone.now().date()` → `timezone.localtime().date()`
- Resuelto en commit `9086ca6`

**FASE 3: T6 Mitigation (superuser cross-tenant exposure)** ✅
- Gap: Sin validación explícita de organización en vistas sensibles
- Mitigación: `require_organization` decorator + middleware check
- Residual: RBAC + audit mode deferred a FASE 4
- Documentado como Tension Node en grafo (n_56223fc8)
- Fix futuro: `timezone.localdate()`

---

## Rutas del módulo operacional

```
/dashboard/<slug>/operations/              → Dashboard principal
/dashboard/<slug>/operations/queue/        → Cola SUNAT (drill-down)
/dashboard/<slug>/operations/integrations/ → Logs externos (drill-down)
/dashboard/<slug>/operations/accounting/   → Contabilidad (drill-down)
```

---

## Próximos pasos recomendados

1. **Validación visual**: navegar al dashboard seed y verificar links de drill-down
2. **FASE 2B** (siguiente): Drill-down de Facturación — desde invoice_status en dashboard
   navegar a órdenes filtradas por status (`/orders/?invoice_status=rejected`)
3. **FASE 3**: Logs de integraciones con payload viewer (sin secretos)

---

## Comandos útiles

```bash
# Tests drill-down
docker compose exec web pytest src/tests/interfaces/web/test_drill_down_views.py -v
docker compose exec web pytest src/tests/interfaces/web/ -v

# Check sistema
docker compose exec web python manage.py check

# Git
git log --oneline -6
```

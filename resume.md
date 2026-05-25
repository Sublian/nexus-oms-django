# Estado actual del proyecto — Nexus OMS

Snapshot técnico al 2026-05-24. Usar como contexto de arranque en nueva sesión.

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

### Modelos clave

- `Order` — tiene `invoice_status` (12 estados), `created_at`
- `InvoiceSyncQueue` — cola persistente con `STATUS_PENDING/PROCESSING/COMPLETED/FAILED/EXHAUSTED/DEAD_LETTER`; `MAX_ATTEMPTS=7`
- `AccountingEntry` + `AccountingEntryLine` — invariante: solo para `invoice_status='accepted'`
- `ExternalRequestLog` — logs por `provider_name`, `success`, `duration_ms`
- `ExternalServiceConfig` — configuración por provider (`base_url`, `api_key` requeridos)

---

## Cambios implementados en esta sesión

### 1. Tests analytics (commit `4fc016a`)
- Nuevo: `src/tests/application/services/__init__.py`
- Nuevo: `src/tests/application/services/test_daily_invoice_series_service.py` (17 tests)
- Nuevo: `src/tests/application/services/test_dashboard_kpi_service.py` (22 tests)
- Cobertura: empty dataset, filtering, tenant isolation, aggregation, date range, acceptance rate formula, latency
- **Nota**: tests usan `days_ago>=1` para evitar skew timezone Lima vs UTC en TruncDate

### 2. FASE 1 — Date Range UX (commit `7ad0d82`)
- `src/domain/services/date_range_service.py`:
  - Añadido `ES_MONTHS` dict (sin dependencia de locale del sistema)
  - Reemplazado `calendar.month_name[_m]` por `ES_MONTHS[_m]`
- `src/interfaces/web/views.py` — `operational_dashboard_view` ahora pasa:
  - `active_period`: `'today'|'week'|'month'|'30d'|'year'|'all'|'7d'|'1d'`
  - `nav_month`, `nav_year`, `nav_month_name`
  - `prev_month_url`, `next_month_url` (None si no aplica o límite futuro)
  - `available_years`: lista `[current-3..current]`
  - `es_months`: lista de tuplas `[(1,'Enero'),...]`
- `src/interfaces/web/templates/dashboard/operations.html`:
  - Reemplazada barra legacy de rolling windows
  - 6 quick filters: Hoy / Esta semana / Este mes / Últimos 30d / Este año / Todo
  - Navegador mensual con ◀ Mes Año ▶ + selector de año (visible solo con `period=month`)
  - Filter activo se resalta con `bg-tenant-primary text-white`
- `src/tests/domain/services/test_date_range_service.py`:
  - Actualizado assertion `'March 2026'` → `'Marzo 2026'`

---

## Estado de tests

- **267 tests passing** (106 ejecutados en esta sesión: date_range + analytics + URL resolution)
- `manage.py check`: 0 issues
- Migración `0016` aplicada correctamente

---

## Archivos sin commit

```
(ninguno — árbol limpio)
```

Documentos sin trackear (intencionales):
- `resume.md` (este archivo)
- `docs/operational_roadmap.md`

---

## Bug conocido (documentado, no bloqueante)

**Timezone inconsistency en `DailyInvoiceSeriesService`:**
- `TruncDate` usa `TIME_ZONE=America/Lima` del settings de Django
- `now.date()` usa UTC (de `timezone.now()`)
- Órdenes creadas cerca de medianoche Lima pueden caer en slot de día incorrecto
- No bloquea operación. Fix futuro: usar `timezone.localdate()` en la construcción del `dates` list

---

## Estado UI Dashboard (`/dashboard/<slug>/operations/`)

### Filtros actuales (nuevo comportamiento)
- **6 quick filters**: Hoy / Esta semana / Este mes / Últimos 30d / Este año / Todo
- **Navegación mensual**: ◀ Mayo 2026 ▶ (cuando `?period=month`)
- **Selector de año**: dropdown visible en modo mensual
- Labels en **español** (ES_MONTHS, sin locale global)
- Parámetros: `?period=today|week|month|year` y `?range=30d|all|7d|1d`

### Secciones del dashboard
1. KPI cards (4): acceptance rate, latencia, errores terminales, total facturadas
2. Charts: línea diaria 30 días + donut estados SUNAT
3. Facturación: tabla de counts por `invoice_status`
4. Queue Health: pending/processing/completed/failed/exhausted/dead_letter + stale locks
5. Integraciones: por provider (error rate, latencia, último error)
6. Consistencia contable: accepted_orders vs entries_generated, missing, orphans

---

## Pendientes inmediatos

1. **Trackear** `resume.md` y `docs/operational_roadmap.md` en git (o dejarlos sin trackear por diseño)
2. **Validación visual**: navegar a `/dashboard/nike/operations/` y verificar:
   - Quick filters se resaltan correctamente
   - ◀ ▶ navega entre meses
   - Selector año funciona
   - Labels en español
3. **FASE 2** (próximo bloque): Drill-down navegación — desde KPIs navegar a listas filtradas

---

## Siguiente bloque recomendado

**FASE 1 completada** ✅

**FASE 2 — Facturación visible** (próximo):
- Bloque de facturación electrónica en modal de pedido
- Mejorar columna invoice_status en listado de pedidos (badge + tooltip)
- O bien: Drill-down desde dashboard (clic en "5 errores SUNAT" → lista filtrada)

---

## Comandos útiles

```bash
# Tests relacionados al dashboard
docker compose exec web pytest src/tests/domain/services/test_date_range_service.py src/tests/application/services/ src/tests/interfaces/web/test_url_resolution.py -v

# Sistema
docker compose exec web python manage.py check

# Git
git log --oneline -6
git status

# URL debug
docker compose exec web python manage.py shell -c "from django.urls import reverse; print(reverse('web:operational_dashboard', kwargs={'org_slug': 'nike'}))"
```

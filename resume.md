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

---

## Estado de tests

- **325 tests** (estimado — no se corrió suite completa)
- **58/58** en tests de UI/drill-down ejecutados en esta sesión
- `manage.py check`: 0 issues

---

## Archivos sin commit

```
(ninguno — árbol limpio)
```

---

## Bug conocido (documentado, no bloqueante)

**Timezone inconsistency en `DailyInvoiceSeriesService`:**
- `TruncDate` usa `TIME_ZONE=America/Lima`, `now.date()` usa UTC
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

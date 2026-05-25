# Operational Dashboard Roadmap — Nexus OMS

Estado actualizado: 2026-05-24

Este documento sirve como guía operativa corta para continuar el desarrollo del Dashboard Operacional sin perder foco ni romper arquitectura.

Complementa:
- docs/resume.md → memoria larga / estado global proyecto
- resume.md (raíz) → snapshot corto sesión actual

---

# Objetivo del módulo

El Dashboard Operacional NO es solo una pantalla visual.

Debe convertirse en el centro de monitoreo operativo del OMS para:

- Facturación electrónica (SUNAT)
- Integraciones externas
- Colas de sincronización
- Consistencia contable
- Observabilidad de errores
- Auditoría operacional
- Diagnóstico rápido
- Trazabilidad por pedido/factura

Inspiración conceptual:
- Stripe Dashboard
- Shopify Admin
- Linear
- Sentry
- Datadog
- Queue monitoring systems

---

# Filosofía de desarrollo

## Prioridad principal

Primero:
1. Observabilidad
2. UX operacional
3. Trazabilidad
4. Datos consistentes
5. Navegación clara

Después:
- refinamientos visuales
- microanimaciones
- optimizaciones prematuras

---

# Qué NO hacer

## NO crear complejidad innecesaria

Evitar:
- overengineering
- CQRS innecesario
- event sourcing
- factories gigantes
- servicios abstractos sin necesidad
- generic repositories
- arquitectura enterprise artificial

El proyecto debe mantenerse:
- simple
- mantenible
- observable
- explícito

---

## NO romper capas

Mantener:

domain/
application/
interfaces/

Reglas:
- interfaces NO accede directo a ORM complejo
- lógica vive en application/domain
- templates solo renderizan
- evitar lógica pesada en views.py

---

## NO convertir el dashboard en "solo KPIs"

El dashboard debe permitir:
- detectar problemas
- navegar al problema
- inspeccionar logs
- entender contexto
- corregir operaciones

KPIs solos NO sirven.

---

## NO esconder errores

Errores deben verse claramente:
- provider
- endpoint
- payload resumido
- status code
- mensaje
- timestamp
- order relacionada

Operaciones necesita visibilidad.

---

# Estado actual

## Ya implementado

### Dashboard operacional base
- KPIs principales
- métricas SUNAT
- integración logs
- consistencia contable
- cola de sincronización
- Chart.js serie temporal

### Servicios analytics
- DailyInvoiceSeriesService
- DashboardKPIService
- DateRangeService

### Tests
39 tests analytics passing:
- test_daily_invoice_series_service.py
- test_dashboard_kpi_service.py

228 tests totales passing.

### FASE 1 — UX operacional ✅ (commit 7ad0d82)
- 6 quick filters: Hoy / Esta semana / Este mes / Últimos 30d / Este año / Todo
- Navegación mensual ◀ Mes Año ▶ con selector de año
- ES_MONTHS: labels en español sin locale global
- active_period context para resaltar filtro activo

### FASE 2A — Drill-down navigation ✅ (commit 99b52c3)
- /operations/queue/?status=pending|stale|exhausted|dead_letter|failed
- /operations/integrations/?provider=<name>&status=error
- /operations/accounting/?filter=missing_entries|orphan_entries
- Links "Ver →" en todas las tarjetas métricas del dashboard
- 22 tests: tenant isolation + filtering behavior

---

# Bug conocido

## Timezone inconsistency

DailyInvoiceSeriesService:
- TruncDate usa TIME_ZONE=America/Lima
- now.date() usa UTC

Riesgo:
órdenes cercanas a medianoche pueden caer en día incorrecto.

NO bloquear desarrollo.
Resolver más adelante usando timezone.localdate().

---

# Roadmap inmediato

# FASE 1 — UX operacional ✅ COMPLETA

# FASE 2A — Drill-down navigation ✅ COMPLETA

# FASE 2B — Drill-down facturación (PRÓXIMO)

Objetivo:
desde dashboard, clic en invoice_status → lista de órdenes filtradas.

Implementar:
- Link desde "Errores Terminales" → /orders/?invoice_status=rejected
- Link desde "En Tránsito" → /orders/?invoice_status=submitted,sync_pending
- Filtro ?invoice_status= en order_list_view (si no existe)
- NO invoice detail avanzado todavía

# FASE 2 — Facturación visible (era FASE 2)

Objetivo original:
hacer visible el ciclo completo de facturación en modal de pedido.

## 1. Date Range UX

Implementar:
- selector mes/año
- navegación prev/next
- quick filters:
  - hoy
  - esta semana
  - este mes
  - últimos 30 días
  - este año
  - todo

Formato:
?period=month&month=5&year=2026

---

## 2. Labels en español

Actualmente:
calendar.month_name devuelve inglés.

Implementar:
ES_MONTHS = {
    1: "Enero",
    ...
}

---

## 3. Drill-down navegación

Desde KPIs permitir navegación hacia:
- pedidos
- factura
- logs
- cola sync

Ejemplos:
- "5 errores SUNAT" → abre lista filtrada
- "2 dead letters" → abre cola filtrada

---

# FASE 2 — Facturación visible

Problema actual:
la factura existe pero casi no tiene visibilidad UX.

Objetivo:
hacer visible el ciclo completo de facturación.

## Implementar

### En modal pedido
Agregar bloque:

Facturación Electrónica:
- estado SUNAT
- código respuesta
- mensaje SUNAT
- serie/número
- hash/cdr
- fecha envío
- fecha aceptación
- provider

---

### En listado pedidos

Mejorar columna:
- badge visual
- tooltip
- quick actions

Estados:
- pending
- submitted
- accepted
- observed
- rejected
- failed

---

### Crear vista detalle factura

Nueva página:
invoice_detail.html

Contenido:
- payload enviado
- respuesta provider
- timeline eventos
- retries
- estado actual
- logs relacionados

IMPORTANTE:
No usar modal gigante.
Usar página dedicada.

---

# FASE 3 — Logs y observabilidad

## Crear pantalla:
Operations → Logs Integraciones

Mostrar:
- provider
- endpoint
- latency
- status code
- error
- request id
- timestamp
- order related

Filtros:
- provider
- errores
- rango fecha
- order id

---

## Vista detalle log

Mostrar:
- payload request
- payload response
- headers relevantes
- retry count
- correlation id

IMPORTANTE:
ocultar secretos/tokens.

---

# FASE 4 — Roles y permisos

Actualmente:
todo visible para superadmin.

Necesario:
RBAC básico.

## Roles iniciales

### Admin
acceso completo

### Operaciones
dashboard + pedidos + logs

### Finanzas
facturación + contabilidad

### Soporte
solo lectura

---

# FASE 5 — Adaptador real SUNAT/Nubefact

IMPORTANTE:
Actualmente Nubefact es mock parcial.

NO intentar "perfección SUNAT" todavía.

Objetivo:
preparar arquitectura adaptador.

## Crear abstracción limpia

interface:
- emitir
- consultar
- anular
- descargar_pdf
- descargar_xml
- descargar_cdr

---

# Seed philosophy

El seed NO debe generar basura random solamente.

Debe generar:
- escenarios reales
- errores reales
- retries
- inconsistencias
- órdenes huérfanas
- dead letters
- accepted sin asiento
- logs mixtos

Objetivo:
que el dashboard se vea vivo.

---

# Reglas para Claude

## IMPORTANTE

### Trabajar por bloques pequeños
Máximo:
- 1 feature
- 1 commit semántico
- tests
- verificación

Evitar sesiones largas de 30-60 minutos.

---

## Siempre ejecutar

Antes de terminar:
- pytest
- manage.py check

---

## Mantener commits pequeños

Formato:
feat(...)
fix(...)
refactor(...)
test(...)

---

## Si contexto crece demasiado

Actualizar:
- resume.md (raíz)

NO modificar docs/resume.md salvo cambios importantes.

Luego:
- commit
- /clear
- nueva sesión

---

# Prioridad actual exacta

## Próximo bloque recomendado

FASE 1:
Date Range UX + labels español + navegación mensual.

NO empezar RBAC todavía.
NO empezar WebSockets todavía.
NO empezar tiempo real todavía.

Primero:
hacer usable y observable el dashboard.
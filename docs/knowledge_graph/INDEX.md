# Index — Nexus OMS Knowledge Graph

**Mapa navegable de 8 regiones conceptuales + puntos de entrada.**

## Regiones y Nodos Core

### 1. Multi-Tenancy Foundation
**Qué es**: Aislación de datos por tenant mediante TenantModel + thread-local context.

- [tenant-isolation-mechanism](./architecture/multi-tenancy.md#isolacion) — Pieza acoplada: TenantModel + OrganizationMiddleware + TenantManager
- [tenant-thread-local](./architecture/multi-tenancy.md#thread-local) — `threading.local()` + set/get/clear
- [tenant-bypass-invariant](./security/tenant-bypass.md) — NUNCA `.all_objects` en código de negocio
- [superuser-org-context](./security/superuser-context.md) — Riesgo: superuser sin `X-Org-ID` puede exponer cross-tenant

**Punto de entrada**: [Arquitectura - Multi-Tenancy](./architecture/multi-tenancy.md)

---

### 2. Order Lifecycle (FSM)
**Qué es**: Máquina de estados de órdenes + pipeline fiscal paralelo (SUNAT).

- [order-fsm-states](./domain/order-fsm.md) — DRAFT → PENDING → PAID → SHIPPED → DELIVERED
- [invoice-status-parallel-fsm](./domain/invoice-fsm.md) — 11 estados ortogonales: pending → processing → submitted → [accepted | rejected | failed]
- [workflow-exactly-once](./application/workflow-once.md) — Guard + `select_for_update()` + flag `workflow_processed`
- [order-audit-trail](./domain/order-audit.md) — `OrderWorkflowLog` + acciones: start, executed, invoicing_triggered, error

**Punto de entrada**: [Dominio - Order Lifecycle](./domain/root.md)

---

### 3. Invoicing Pipeline (SUNAT)
**Qué es**: Facturación en 3 fases: crear → sincronizar → contabilizar.

- [invoice-pipeline-architecture](./domain/invoice-pipeline.md) — Fase 1 (async trigger) → Fase 2 (create via Nubefact) → Fase 3 (sync via Beat)
- [invoice-idempotency-guards](./domain/invoice-idempotency.md) — `select_for_update()` + check `invoice_external_id` + check status `processing`
- [invoice-sync-queue-backoff](./domain/invoice-sync-queue.md) — Backoff exponencial + locked_at + estados terminales (EXHAUSTED)
- [nubefact-error-taxonomy](./domain/nubefact-errors.md) — PermanentError (400/401/403/422) vs TemporaryError (5xx)
- [accounting-entry-invariant](./domain/accounting-entry.md) — OneToOne a Order, solo si `invoice_status == 'accepted'`
- [invoice-provider-abstraction](./domain/invoice-provider.md) — ABC + NubefactClient | MockNubefactClient

**Punto de entrada**: [Dominio - Invoicing Pipeline](./domain/invoice-pipeline.md)

---

### 4. Stock Management
**Qué es**: Ajuste de stock via Django signals + movimientos auditados.

- [stock-signals-design](./domain/stock-signals.md) — `OrderItem.create` → `adjust_stock_on_sale` → OUTPUT + `select_for_update()`
- [stock-race-condition-risk](./domain/stock-signals.md#race-condition) — Signal requiere transacción DB real; tests deben usar `django_db(transaction=True)`
- [stock-movement-audit](./domain/stock-movement.md) — Registro completo: INPUT | OUTPUT | RETURN + FK a Order

**Punto de entrada**: [Dominio - Stock Management](./domain/stock-signals.md)

---

### 5. Financial Services
**Qué es**: Exchange rates + COGS estimation + margen neto.

- [exchange-rate-chain](./domain/exchange-rate.md) — Fallback: DB → APIMigo → ayer → hardcoded 3.80/3.75
- [cogs-estimation](./domain/cogs-estimation.md) — Último `PurchaseOrderItem.unit_cost` o fallback 50% venta (impreciso)
- [finance-service-duplication](./domain/finance-duplication.md) — `finance_service.py` + `order_service.py` duplican lógica (deuda técnica)

**Punto de entrada**: [Dominio - Financial Services](./domain/root.md#financial)

---

### 6. Async & Scheduling (Celery)
**Qué es**: Beat scheduling + eager mode en tests.

- [celery-beat-schedule](./infrastructure/celery-beat.md) — 3 jobs: weekly reports, exchange 06:00, sync invoices 60s
- [celery-test-mode](./infrastructure/celery-test.md) — `CELERY_TASK_ALWAYS_EAGER=True` → sync execution sin Redis

**Punto de entrada**: [Infraestructura - Celery](./infrastructure/celery-beat.md)

---

### 7. Application Layer (En Desarrollo)
**Qué es**: Use cases + services (minimal, inconsistente).

- [application-layer-minimal](./application/layer-minimal.md) — Solo 3 use cases; `create_order` en domain, no en application
- [dependency-injection-partial](./application/di-partial.md) — DI existe donde se necesitó testear, no como patrón uniforme

**Punto de entrada**: [Arquitectura - Application Layer](./architecture/root.md#application)

---

### 8. API & Interfaces
**Qué es**: Dual interface (REST API + Web Dashboard).

- [dual-interface-architecture](./interfaces/dual-interface.md) — API REST (/api/v1/) + JWT vs Web (/dashboard/) + sessions
- [jwt-claims-tenant-context](./interfaces/jwt-claims.md) — Extiende JWT: email + role + organization_id

**Punto de entrada**: [Arquitectura - Interfaces](./architecture/root.md#interfaces)

---

## Decisiones Arquitectónicas (ADRs)

- [ADR-001: Why Application Guards BEFORE PostgreSQL RLS](./decisions/ADR-001.md)

---

## Invariantes Críticas (Resumen)

```
1. TENANT FILTER:      Nunca .all_objects en código de negocio
2. INVOICE DEDUP:      Si order.invoice_external_id existe → SKIP
3. WORKFLOW ONCE:      order.workflow_processed es canonical
4. STOCK ATOMIC:       OrderItem creation → signal → decrement (transacción)
5. ACCOUNTING GATE:    AccountingEntry solo si invoice_status == 'accepted'
6. FSM TRANSITIONS:    Usar @transition decorators, nunca setear directo
7. THREAD CLEANUP:     OrganizationMiddleware DEBE limpiar al final
```

---

## Tensiones Activas

| ID  | Tensión | Urgencia |
|-----|---------|----------|
| T1  | Duplicación finance_service / order_service | Media |
| T2  | create_order en domain vs application | Media |
| T3  | COGS fallback 50% impreciso | Alta |
| T4  | Sin circuit breaker para APIMigo | Media |
| T5  | DI inconsistente | Baja |
| T6  | Superuser sin X-Org-ID expone cross-tenant | Alta |
| T7  | Tests no cubren comportamiento real Celery | Media |

---

## Mapa de Transición

```
README.md
  ├→ INDEX.md (estás aquí)
  ├→ project/root.md (Roadmap macro)
  ├→ architecture/root.md (Stack técnico)
  ├→ security/root.md (S0 + S1 + S2 boceto)
  ├→ domain/root.md (Reglas de negocio)
  ├→ infrastructure/root.md (Persistencia + Celery)
  └→ decisions/ (ADRs)
```

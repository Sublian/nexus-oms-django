# Understanding Graph Snapshot — nexus-oms-django

> **Generado**: 2026-06-14  
> **Propósito**: Respaldo de comprensión del grafo para consulta futura y onboarding rápido de nuevas sesiones.  
> **Formato**: Nodos con trigger + edges con tipo + invariantes + tensiones activas.

---

## Orientación rápida (equivale a `graph_skeleton`)

| Región | Hubs principales | Actividad reciente |
|--------|------------------|--------------------|
| **Core Domain** | `Order` (FSM), `TenantModel`, `Stock` | FSM + signals de stock |
| **Invoicing Pipeline** | `InvoiceSyncQueue`, `create_invoice_task`, `NubefactClient` | Cola de sincronización SUNAT |
| **Multi-Tenancy** | `TenantManager`, `OrganizationMiddleware`, thread-local | Fundación de seguridad |
| **Async / Celery** | `sync_pending_invoices_task`, `generate_weekly_all_orgs`, `sync_daily_exchange_rate` | Beat scheduling |
| **Application Layer** | `OrderWorkflowService`, `CreateInvoiceUseCase`, `InvoiceStatusQueryUseCase` | En desarrollo activo |

---

## Regiones del grafo

### REGIÓN 1 — Multi-Tenancy Foundation

#### Nodo: `tenant-isolation-mechanism`
- **Trigger**: `foundation`
- **Contenido**: La aislación de datos por tenant se implementa con 3 piezas acopladas:  
  1. `TenantModel` (abstract) — `organization` FK + `TenantManager` + `all_objects`  
  2. `OrganizationMiddleware` — resuelve tenant desde header `X-Org-ID` (API) o slug de URL (Web), lo setea en thread-local  
  3. `TenantManager.get_queryset()` — aplica `.filter(organization_id=org_id)` automáticamente en cada query
- **Archivos**: `src/infrastructure/models.py`, `src/infrastructure/multitenancy/`

#### Nodo: `tenant-thread-local`
- **Trigger**: `foundation`
- **Contenido**: `threading.local()` en `thread_local.py` — `set_current_organization(id)` / `get_current_organization()` / `clear_current_organization()`. El middleware setea al inicio del request y limpia al final. Sin este clear, hay riesgo de data leakage entre requests en el mismo thread.
- **Edge → `tenant-isolation-mechanism`**: `refines` — es la implementación concreta del mecanismo

#### Nodo: `tenant-bypass-invariant`
- **Trigger**: `foundation`
- **Contenido**: **NUNCA usar `.all_objects` en código de negocio.** `.all_objects` es el Manager base de Django sin filtro de tenant. Solo permitido en admin Django, scripts de migración de datos, y tests que testean cross-tenant explícitamente. Bypassear = data leak entre clientes.
- **Edge → `tenant-isolation-mechanism`**: `consequence` — viola la garantía de aislación

#### Nodo: `superuser-org-context`
- **Trigger**: `surprise`
- **Contenido**: Los superusuarios pueden especificar cualquier org via header `X-Org-ID`. En `TenantViewMixin.get_organization()` se permite esto. El peligro: si el superuser no envía el header, el middleware no setea contexto → queries sin filtro pueden devolver datos de todas las orgs. Los tests de permisos deben cubrir este caso.
- **Edge → `tenant-bypass-invariant`**: `tension` — caso borde donde el invariante puede violarse silenciosamente

---

### REGIÓN 2 — Order Lifecycle (FSM)

#### Nodo: `order-fsm-states`
- **Trigger**: `foundation`
- **Contenido**: `Order.status` usa `django-fsm`. Transiciones válidas definidas en `order_constants.py`:  
  `DRAFT → [PENDING, COURTESY, CANCELLED]`  
  `PENDING → [PAID, CANCELLED]`  
  `PAID → [SHIPPED, CANCELLED]`  
  `SHIPPED → [DELIVERED, RETURNED]`  
  Ramas terminales: `DELIVERED`, `CANCELLED`, `RETURNED`
- **Archivos**: `src/domain/models/sales.py`, `src/domain/models/order_constants.py`

#### Nodo: `invoice-status-parallel-fsm`
- **Trigger**: `surprise`
- **Contenido**: `Order` tiene DOS máquinas de estado independientes: `status` (ciclo de vida del pedido) e `invoice_status` (ciclo de vida fiscal con SUNAT). Son ortogonales. `invoice_status` tiene 11 estados: `pending → processing → submitted → accepted | observed | rejected | failed | dead_letter | exhausted`. La orden puede estar DELIVERED con invoice FAILED.
- **Edge → `order-fsm-states`**: `refines` — añade una segunda dimensión de estado al mismo modelo

#### Nodo: `workflow-exactly-once`
- **Trigger**: `foundation`
- **Contenido**: `OrderWorkflowService.handle_order_paid()` garantiza exactamente una ejecución por orden via:  
  1. Guard: `order.workflow_processed == True` → skip (fast path)  
  2. `_claim_workflow_lock()` → `select_for_update()` + check idempotencia atómica  
  3. Post-ejecución: setear `workflow_processed=True`  
  El flag `workflow_processed` es el canonical source of truth.
- **Archivos**: `src/application/services/order_workflow_service.py`

#### Nodo: `order-audit-trail`
- **Trigger**: `consequence`
- **Contenido**: `OrderWorkflowLog` registra cada transición del workflow (action, metadata JSONField, timestamp). Las acciones son: `start`, `action_executed`, `invoicing_triggered`, `error`, `completed`, `skipped_*`. Esto permite debugging forense de por qué una orden no fue facturada.
- **Edge → `workflow-exactly-once`**: `learned_from` — el audit log nació del need de debugging del lock mechanism

---

### REGIÓN 3 — Invoicing Pipeline (SUNAT)

#### Nodo: `invoice-pipeline-architecture`
- **Trigger**: `model`
- **Contenido**: Pipeline de facturación en 3 fases:  
  **Fase 1** (síncrona, en el workflow): `create_invoice_task.delay(order.id)` — disparo asíncrono  
  **Fase 2** (Celery task): `CreateInvoiceUseCase.execute(order)` → `NubefactClient.create_invoice()` → HTTP POST → guarda `invoice_external_id`  
  **Fase 3** (Beat cada 60s): `sync_pending_invoices_task` → fan-out de `sync_single_invoice_task` por cada entry en `InvoiceSyncQueue` → `InvoiceStatusQueryUseCase` → consulta estado a Nubefact/SUNAT → si `accepted` → crea `AccountingEntry`
- **Archivos**: `src/application/usecases/`, `src/domain/tasks/invoice_tasks.py`, `src/domain/tasks/sync_invoice_tasks.py`

#### Nodo: `invoice-idempotency-guards`
- **Trigger**: `foundation`
- **Contenido**: Tres guards en `create_invoice_task`:  
  1. `select_for_update()` → lock pesimista al inicio  
  2. Si `order.invoice_external_id` existe → SKIP (ya creada)  
  3. Si `order.invoice_status == 'processing'` → SKIP (otro worker en vuelo)  
  Estos guards son atómicos y deben mantenerse en orden. Perderlos = facturas duplicadas en SUNAT (consecuencia fiscal grave).
- **Edge → `invoice-pipeline-architecture`**: `refines`

#### Nodo: `invoice-sync-queue-backoff`
- **Trigger**: `decision`
- **Contenido**: `InvoiceSyncQueue` implementa backoff exponencial con tiempos fijos: `[60, 300, 900, 1800, 3600, 21600, 86400]` segundos. Lock pessimista via `locked_at` evita doble polling. Estados terminales: `COMPLETED`, `FAILED`, `DEAD_LETTER`, `EXHAUSTED`. Una entry llega a `EXHAUSTED` cuando supera el máximo de intentos y ya no se reintentará automáticamente — requiere intervención manual.
- **Edge → `invoice-pipeline-architecture`**: `consequence`

#### Nodo: `nubefact-error-taxonomy`
- **Trigger**: `foundation`
- **Contenido**: Dos clases de error con comportamiento distinto:  
  - `NubefactPermanentError` (HTTP 400, 401, 403, 422): No reintentar. La orden tiene un problema de datos. Requiere corrección manual antes de reintentar.  
  - `NubefactTemporaryError` (HTTP 500, 502, 503, 504): Reintentar con backoff. Falla del servicio externo, transitoria.
- **Archivos**: `src/domain/exceptions/`

#### Nodo: `accounting-entry-invariant`
- **Trigger**: `foundation`
- **Contenido**: `AccountingEntry` (OneToOne a Order) SOLO se crea cuando `invoice_status == 'accepted'`. Tiene un snapshot del estado fiscal: `invoice_external_id`, `amount_gross`, `amount_tax`, `amount_net`. Esta invariante garantiza que solo órdenes con factura aceptada por SUNAT tienen registro contable.
- **Edge → `invoice-pipeline-architecture`**: `consequence`

#### Nodo: `invoice-provider-abstraction`
- **Trigger**: `decision`
- **Contenido**: `InvoiceProvider` (ABC) permite intercambiar `NubefactClient` (producción) por `MockNubefactClient` (tests/desarrollo). La selección es por `CompanyInvoiceConfig.provider_type` (`nubefact` | `mock`). Cada tenant puede tener su propio config. Esto permite testing real sin llamadas HTTP.
- **Edge → `nubefact-error-taxonomy`**: `learned_from`

---

### REGIÓN 4 — Stock Management

#### Nodo: `stock-signals-design`
- **Trigger**: `decision`
- **Contenido**: El ajuste de stock se hace via Django signals post-save, no en los servicios directamente:  
  - `OrderItem` creado → `adjust_stock_on_sale` → descuenta stock + crea `StockMovement.OUTPUT`  
  - `PurchaseOrder` → RECEIVED → `update_stock_on_received_po` → incrementa stock + `StockMovement.INPUT`  
  - `OrderReturn` con `reentered_to_stock=True` → `handle_stock_on_return` → incrementa + `StockMovement.RETURN`  
  Todos usan `select_for_update()` para evitar race conditions.
- **Archivos**: `src/domain/signals.py`

#### Nodo: `stock-race-condition-risk`
- **Trigger**: `tension`
- **Contenido**: El `select_for_update()` en los signals previene race conditions en producción. Sin embargo, en tests el signal requiere una transacción DB real activa — no funciona con mocks simples. Los tests de stock deben usar `pytest.mark.django_db(transaction=True)` o mockear el signal completo. Si se olvida, los tests pasan pero el stock no se ajusta.
- **Edge → `stock-signals-design`**: `tension`

#### Nodo: `stock-movement-audit`
- **Trigger**: `consequence`
- **Contenido**: `StockMovement` registra cada cambio de stock con `movement_type` (INPUT, OUTPUT, RETURN), `reason`, y FK a `Order` si aplica. Es el audit trail del inventario — permite reconciliar discrepancias entre stock contado físicamente y stock en DB.

---

### REGIÓN 5 — Financial Services

#### Nodo: `exchange-rate-chain`
- **Trigger**: `model`
- **Contenido**: `ExchangeService.get_current_rate()` implementa una cadena de fallback:  
  1. Busca `ExchangeRate` de hoy en DB (cache)  
  2. Si no existe → `APIMigoClient.get_exchange_rate(hoy)` → crea en DB  
  3. Si APIMigo falla → intenta con `ayer`  
  4. Fallback final hardcodeado: 3.80 venta / 3.75 compra (USD)  
  El fallback hardcodeado es un riesgo si el tipo de cambio varía significativamente.
- **Archivos**: `src/domain/services/order_service.py`

#### Nodo: `cogs-estimation`
- **Trigger**: `tension`
- **Contenido**: El cálculo de margen neto en `get_net_margin_report()` estima COGS buscando el último `PurchaseOrderItem.unit_cost` para ese producto. Si no existe, usa un fallback del 50% del precio de venta. Este fallback es un supuesto arbitrario que puede distorsionar los reportes financieros significativamente en productos sin historial de compra.
- **Edge → `exchange-rate-chain`**: `tension` — dos aproximaciones financieras con fallbacks imprecisos

#### Nodo: `finance-service-duplication`
- **Trigger**: `tension`
- **Contenido**: `finance_service.py` y `order_service.py` duplican `calculate_expected_cash()` y `get_net_margin_report()`. Ambas implementaciones deben mantenerse en sincronía. Si se actualiza una lógica de cálculo en una, la otra queda desactualizada. **Deuda técnica activa**.

---

### REGIÓN 6 — Async & Scheduling

#### Nodo: `celery-beat-schedule`
- **Trigger**: `foundation`
- **Contenido**: Tres jobs programados en `config/settings/base.py → CELERY_BEAT_SCHEDULE`:  
  - `generate-weekly-reports`: lunes 00:00 UTC → itera todas las orgs → fan-out  
  - `sync-exchange-6am`: diariamente 06:00 UTC → actualiza tipo de cambio  
  - `sync-pending-invoices`: **cada 60 segundos** → fan-out masivo de sincronización SUNAT  
  El job de 60s es crítico: si Celery Beat se detiene, la cola SUNAT se acumula indefinidamente.
- **Archivos**: `config/settings/base.py`, `config/celery.py`

#### Nodo: `celery-test-mode`
- **Trigger**: `foundation`
- **Contenido**: `config/settings/testing.py` setea `CELERY_TASK_ALWAYS_EAGER=True`. Las tasks se ejecutan síncronamente en el mismo thread, sin Redis. Esto significa que en tests, `task.delay()` = `task()` directamente. Consecuencia: los tests no cubren errores de serialización de argumentos ni comportamiento real de la cola.

---

### REGIÓN 7 — Application Layer (En Desarrollo)

#### Nodo: `application-layer-minimal`
- **Trigger**: `tension`
- **Contenido**: La capa `application/` tiene solo 3 use cases + 1 service. `OrderService.create_order()` y `OrderService.process_return()` viven en `domain/services/` cuando deberían vivir en `application/usecases/`. El dominio orquesta infraestructura directamente en lugar de que la aplicación lo haga. Esto dificulta testing unitario de la orquestación.
- **Archivos**: `src/application/`

#### Nodo: `dependency-injection-partial`
- **Trigger**: `surprise`
- **Contenido**: `CreateInvoiceUseCase` y `OrderWorkflowService` aceptan inyección en constructor (`provider`, `logger`). Pero `OrderService` llama directamente a `APIMigoClient` sin inyección. La DI es inconsistente: existe donde se necesitó testear, no como patrón arquitectónico uniforme.

---

### REGIÓN 8 — API & Interfaces

#### Nodo: `dual-interface-architecture`
- **Trigger**: `foundation`
- **Contenido**: El sistema expone dos interfaces independientes:  
  - **API REST** (`/api/v1/`): DRF viewsets + JWT → para clientes externos / frontend SPA  
  - **Web Dashboard** (`/dashboard/{org_slug}/`): Django views + HTMX + Tailwind CDN → para usuarios internos  
  Comparten modelos de dominio pero tienen autenticación diferente (JWT vs sessions) y resolución de tenant diferente (header vs URL slug).

#### Nodo: `jwt-claims-tenant-context`
- **Trigger**: `decision`
- **Contenido**: `CustomTokenObtainPairSerializer` extiende el JWT con `{email, role, organization_id}`. Esto permite que el cliente API construya requests con el contexto correcto sin una llamada adicional al servidor. La API confía en `organization_id` del JWT para resolver el tenant en requests sin `X-Org-ID` header.

---

## Edges globales (conexiones cross-región)

| Desde | Hacia | Tipo | Por qué |
|-------|-------|------|---------|
| `tenant-isolation-mechanism` | `stock-signals-design` | `consequence` | Los signals operan bajo el contexto de tenant activo en el thread |
| `invoice-idempotency-guards` | `workflow-exactly-once` | `learned_from` | Mismo patrón de lock pessimista + flag aplicado en dos niveles |
| `order-fsm-states` | `invoice-pipeline-architecture` | `questions` | ¿Cuándo exactamente se dispara el pipeline? Al transicionar a PAID |
| `celery-test-mode` | `stock-race-condition-risk` | `invalidates` | En tests eager, `select_for_update` no aplica igual — reduce la cobertura real del race condition |
| `application-layer-minimal` | `workflow-exactly-once` | `tension` | El workflow service está en `application/` pero `create_order` en `domain/services/` — inconsistencia de capas |
| `finance-service-duplication` | `cogs-estimation` | `refines` | La duplicación incluye la misma lógica imprecisa de COGS |
| `exchange-rate-chain` | `celery-beat-schedule` | `consequence` | El job de 06:00 UTC garantiza que la cadena de fallback rara vez llegue al hardcoded |

---

## Invariantes críticas (para orientación rápida)

```
1. TENANT FILTER: Nunca .all_objects en código de negocio. Siempre .objects (TenantManager).

2. INVOICE DEDUP: Si order.invoice_external_id existe → SKIP. No reintentar.

3. WORKFLOW ONCE: order.workflow_processed es el flag canónico. select_for_update en el lock.

4. STOCK ATOMIC: OrderItem creation → signal → stock decrement. Siempre en transacción.

5. ACCOUNTING GATE: AccountingEntry solo existe si invoice_status == 'accepted'.

6. FSM TRANSITIONS: Usar @transition decorators solamente. Nunca setear Order.status directamente.

7. THREAD LOCAL CLEANUP: OrganizationMiddleware DEBE limpiar thread-local al final del request.
```

---

## Tensiones activas (requieren resolución futura)

| ID | Tensión | Nodos involucrados | Urgencia |
|----|---------|-------------------|---------|
| T1 | Duplicación `finance_service` / `order_service` | `finance-service-duplication` | Media |
| T2 | `create_order` en domain en lugar de application | `application-layer-minimal` | Media |
| T3 | COGS fallback 50% impreciso en reportes financieros | `cogs-estimation` | Alta |
| T4 | Sin circuit breaker para APIMigo | `exchange-rate-chain` | Media |
| T5 | DI inconsistente (exists donde se necesitó, no como patrón) | `dependency-injection-partial` | Baja |
| T6 | Superuser sin `X-Org-ID` puede exponer datos cross-tenant | `superuser-org-context` | Alta |
| T7 | Tests no cubren comportamiento real de cola Celery | `celery-test-mode` | Media |

---

## Mapa de archivos clave → nodos del grafo

```
src/infrastructure/models.py              → tenant-isolation-mechanism
src/infrastructure/multitenancy/          → tenant-isolation-mechanism, tenant-thread-local
src/domain/models/sales.py               → order-fsm-states, invoice-status-parallel-fsm
src/domain/models/order_constants.py     → order-fsm-states
src/domain/models/invoicing.py           → invoice-sync-queue-backoff
src/domain/models/accounting.py          → accounting-entry-invariant
src/domain/signals.py                    → stock-signals-design
src/domain/tasks/invoice_tasks.py        → invoice-idempotency-guards
src/domain/tasks/sync_invoice_tasks.py   → invoice-sync-queue-backoff
src/domain/tasks/reporting_tasks.py      → celery-beat-schedule
src/domain/services/order_service.py     → exchange-rate-chain, cogs-estimation
src/application/services/order_workflow_service.py → workflow-exactly-once
src/application/usecases/create_invoice.py         → invoice-idempotency-guards
src/application/usecases/query_invoice_status.py   → invoice-sync-queue-backoff
src/application/providers/factory.py              → invoice-provider-abstraction
src/infrastructure/services/apimigo.py            → exchange-rate-chain
src/interfaces/api/views.py                        → dual-interface-architecture
config/settings/base.py                            → celery-beat-schedule
config/celery.py                                   → celery-beat-schedule
```

---

## Stack técnico (referencia rápida)

| Componente | Tecnología | Versión |
|------------|-----------|---------|
| Framework | Django | 6.0.3 |
| API | Django REST Framework | 3.17.1 |
| Auth API | djangorestframework-simplejwt | 5.4.0 |
| FSM | django-fsm | 3.0.1 |
| Frontend | HTMX + Tailwind CDN | 1.27.0 |
| Task Queue | Celery + Redis | 5.6.3 |
| DB | PostgreSQL via psycopg3 | 3.3.3 |
| PDF | WeasyPrint | 68.1 |
| API Docs | drf-spectacular (Swagger) | 0.29.0 |
| Tests | pytest + pytest-django + pytest-cov | 9.0.2 |

---

## Cómo usar este snapshot en una nueva sesión

1. **Orientación** (30s): leer sección "Orientación rápida" y la tabla de regiones.
2. **Tarea específica**: buscar el nodo relevante en "Mapa de archivos clave → nodos".
3. **Antes de modificar**: leer las invariantes críticas y tensiones activas.
4. **Después de implementar**: si algo cambió en la comprensión del sistema, actualizar el grafo real con `graph_batch` (desde una sesión en el directorio del proyecto).

> **Nota**: Este snapshot es una fotografía estática. El grafo real en `projects/default/store.db` puede tener nodos más recientes. Este archivo es un fallback, no la fuente de verdad.

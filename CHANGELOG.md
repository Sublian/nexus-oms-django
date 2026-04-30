# CHANGELOG

## [2.2.0] - 2026-04-29 (Fase 1.5 Hardening) ✅ COMPLETO

### PASO 6 ✅ — Punto de extensión para Fase 2
- `OrderWorkflowService._trigger_invoicing(order)` — placeholder para Nubefact
- Se ejecuta en flujo normal (post-pago)
- Sin dependencias externas: solo log
- Test verifica que se invoca: `test_invoicing_trigger_is_called`
- Fase 2: reemplazar body con llamada real a Nubefact sin romper diseño

### PASO 5 ✅ — Refuerzo de tests (cobertura robusta)
- +1 test: `test_all_events_logged_in_order` — valida secuencia START → ACTION → INVOICING → END
- Total: 12 tests (7 unitarios mocked + 4 integracion + 1 secuencia)
- Cobertura de casos clave: flujo correcto, idempotencia, guardias, persistencia, extensión

### PASO 4 ✅ — Tests de integración (DB real)
- `test_order_workflow_integration.py` — 4 tests con Django ORM real
  - Persistencia: `workflow_processed` queda en DB tras ejecución
  - Idempotencia real: segunda llamada en objeto nuevamente cargado no re-ejecuta
  - Guardias: estado DRAFT skipped, PENDING skipped
  - Ciclo completo: PENDING → PAID → workflow → DB verifica estado
- Confianza real en el sistema: persistencia probada contra DB de test

### PASO 3 ✅ — Mejora de logging (observabilidad)
- Formato estandarizado: `[OrderWorkflow][order_id=X][action=Y][details...]`
- Eventos clave: START, VALIDATION_FAIL, SKIP_ALREADY_PROCESSED, ACTION_EXECUTED, INVOICING_TRIGGERED, END
- Logs filtrable por `order_id` — fácil auditoría sin herramientas externas
- +2 tests: uno para estructura de logs, uno para invoicing trigger

### PASO 2 ✅ — Normalización de estados
- `src/domain/models/order_constants.py` — `OrderStatus` clase con constantes (DRAFT, PENDING, PAID, SHIPPED, DELIVERED, COMPLETED, RETURNED, CANCELLED)
- `OrderStatus.CHOICES` reemplaza STATUS_CHOICES
- `OrderStatus.VALID_TRANSITIONS` reemplaza VALID_TRANSITIONS
- `Order.status` default usa `OrderStatus.DRAFT`
- `OrderWorkflowService` y todas las vistas usan constantes, no strings sueltos
- Riesgo silencioso eliminado: no hay más 'PAID' vs "paid" vs 'paid'

### PASO 1 ✅ — Persistencia real del workflow
- Campo `Order.workflow_processed: BooleanField(default=False)` — idempotencia persistente
- Migration `0005_order_workflow_processed` aplicada
- `OrderWorkflowService.handle_order_paid()` ahora valida contra flag persistente
- Idempotencia real: reiniciar app → flag se mantiene
- Tests unitarios verifican comportamiento con campo persistente

---

## [2.1.0] - 2026-04-29

### Added
- `OrderWorkflowService` (`src/application/services/order_workflow_service.py`) — punto único de orquestación para el flujo de pago de órdenes
- Logger dedicado `order_workflow` (`src/infrastructure/logger.py`) con handler de consola
- Configuración `LOGGING["order_workflow"]` en `config/settings/base.py`
- Integración explícita en `order_pay_modal_view`: workflow se ejecuta después de `order.status = 'PAID'`, antes de `order.save()`
- 5 tests unitarios en `src/tests/application/test_order_workflow_service.py` (flujo correcto, idempotencia, estado inválido)

### Architecture
- Crea capa `src/application/` — orchestration layer según clean architecture del proyecto
- Flujo explícito sin signals ni lógica oculta en modelos
- Base preparada para Fase 2: invoicing (Nubefact) e inventory

---

## [2.0.1] - 2026-04-26

### Fixed
- **Order item edit:** Fila de tabla principal ahora se actualiza cuando se cierra modal tras editar cantidad (OOB swap agregado)
- **Order item delete:** Modal de confirmación personalizado en lugar del `hx-confirm` nativo del navegador
  - Nuevo endpoint: `order_item_delete_confirm` (GET) retorna modal personalizado
  - Nuevo template: `item_delete_modal.html` con contexto inteligente (nota obligatoria si es último item)
  - Z-index ajustado (z-60) para sobreponer sobre modal de orden
  - Mayor control UX sobre eliminaciones de items

### Added
- New view: `order_item_delete_confirm_view` - Renderiza modal de confirmación de delete
- New template: `item_delete_modal.html` - Modal personalizado con dos flujos (último item vs otros items)
- New URL route: `/orders/<id>/items/<id>/delete/confirm/` (GET)
- Nested modal container `#nested-modals-here` en order_detail_modal

### Changed
- `order_item_edit_view`: Response ahora incluye OOB swap de fila `order-row-{id}` para actualizar tabla principal
- `order_item_delete_view`: Response ahora incluye OOB swap de fila para consistency
- Botones delete en templates: Cambio de `hx-post` directo a `hx-get` de confirm modal

---

## [2.0.0] - 2026-04-24

### Completed Block 1: Order Management ✅
- Full order lifecycle: DRAFT → PENDING → PAID → SHIPPED → DELIVERED → COMPLETED
- Inline item editing with stock validation
- Item deletion with auto-cancellation for empty orders
- Payment modal with method selection (CASH/CARD/TRANSFER/WALLET)
- PDF invoice generation (SUNAT-style)
- Stock control with atomic transactions
- Multi-tenant safety with TenantManager

### Infrastructure
- Multi-tenancy: Thread-local organization context
- Django settings per environment (local/testing/production)
- Docker Compose stack (web, db, redis, celery, flower)
- Clean Architecture: domain → application → infrastructure → interfaces
- JWT authentication for API, sessions for web
- GitHub Actions CI/CD
- Test coverage: 91% (61 tests)

### Modules
- **Clientes:** Full CRUD, search, stats, document validation (RENIEC/SUNAT via APIMigo)
- **Productos:** CRUD, categories, stock by warehouse, SKU uniqueness
- **Órdenes:** Complete lifecycle, delivery modes (PICKUP/DELIVERY), shipping fees
- **Finanzas:** Exchange rate sync, net margin calculations

---

## [1.0.0] - Initial Release
- MVP: Django + DRF + HTMX foundation
- Basic order creation and listing

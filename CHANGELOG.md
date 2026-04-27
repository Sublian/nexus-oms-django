# CHANGELOG

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

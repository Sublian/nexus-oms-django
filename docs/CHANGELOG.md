## [2.0.0] - 2026-04-26

**🎯 Block 1 COMPLETE: Core Order Lifecycle + Inventory Management + Edge Cases**

### Hitos Alcanzados
- **Deuda técnica resuelta:** Fixed double-decrement bug donde stock se restaba 2x al crear orden (decrement directo en view + signal). Ahora solo signal maneja stock.
- **Modal enriquecido:** Orden detail modal muestra delivery_type (Delivery/Pickup) y shipping_fee en resumen de cobro.
- **Edit inline de OrderItem:** En órdenes DRAFT/PENDING, ícono lápiz → form HTMX inline para cambiar cantidad (con validación de stock). Ícono basura → confirmar y eliminar, restaurando stock.
- **Stock recalc:** Helper `_recalculate_order_totals()` recalcula subtotal/IGV/total tras cualquier cambio de items.
- **Validación PAID:** Antes de transicionar a PAID, sanity check que stock no sea negativo (previene race conditions).

### Added
- `order_item_edit_view()` — GET: inline form; POST: update qty, validate stock, recalc totals
- `order_item_delete_view()` — DELETE: remove item, restore stock, recalc totals
- `_recalculate_order_totals()` — helper para recalcular financieros tras cambios
- Routes: `order-item-edit`, `order-item-delete`
- Template: `orders/partials/item_edit_form.html` — formulario inline con validación
- Order detail modal: delivery type badge + shipping_fee row (if > 0)

### Fixed
- Double-decrement bug: removed manual stock decrement in `order_create_view` (lines 293-294)
- Order detail modal: missing delivery_type and shipping_fee info
- Race condition safeguard in `order_pay_modal_view`: stock validation before PAID transition

### Changed
- `order_detail_modal.html` — added delivery info section, shipping_fee row, edit/delete buttons on items (DRAFT/PENDING only)
- `order_item_edit_view` — new fields to support inline quantity editing with stock validation
- Stock handling: single source of truth now via `adjust_stock_on_sale` signal + `select_for_update()` atomicity

**Block 1 Status:** ✅ COMPLETE — Order lifecycle (create→draft→edit items→pay→ship→deliver) fully functional with inventory management.

---

## [1.9.0] - 2026-04-26

**📦 Gestión de Productos & SKUs — Inventario, Trazabilidad y CRUD Completo**

### Hitos Alcanzados
- **Catálogo de Productos:** Lista paginada con búsqueda por nombre/SKU/descripción, filtro por estado (activo/suspendido/todos) y filtro por categoría. Badges de stock con colores según nivel (rojo=0, ámbar≤5, verde>5).
- **Detalle de Producto:** Card con información completa, resumen de stock total, tabla de stock por almacén con fecha de última actualización, y tabla de trazabilidad de pedidos con cantidad vendida y subtotal por orden.
- **CRUD de Productos:** Formulario único (create/edit) con: find-or-create de categoría (insensible a mayúsculas), campo de stock inicial al crear (almacén + cantidad, sección opcional expandible), validación de SKU único por tenant y precio positivo.
- **Suspensión de Productos:** Toggle activo/suspendido vía POST con redirección al detalle. Productos suspendidos quedan visibles pero con opacidad reducida en el listado.
- **Sidebar activado:** El enlace "Productos & SKUs" ahora apunta a `/products/` con highlight activo.

### Added
- `product_list_view` — listado con búsqueda, filtros, paginación y anotación de stock total
- `product_detail_view` — detalle con stock por almacén y trazabilidad de órdenes
- `product_create_view` — creación con categoría find-or-create y stock inicial opcional
- `product_edit_view` — edición con validación de SKU único (excluyendo self)
- `product_toggle_active_view` — toggle suspender/activar vía POST
- `_product_form_context()` — helper DRY para contexto de formularios create/edit
- `templates/products/product_list.html` — tabla con tabs de estado y badges de stock
- `templates/products/product_detail.html` — info, stock por almacén, trazabilidad de pedidos
- `templates/products/product_form.html` — formulario con Alpine.js (categoría autocomplete, stock inicial expandible)
- Rutas: `product-list`, `product-create`, `product-detail`, `product-edit`, `product-toggle`

### Changed
- `sidebar.html` — "Productos & SKUs" apunta a `web:product-list` con highlight activo en `/products/*`

---

## [1.8.0] - 2026-04-25

**👥 Directorio de Clientes — CRUD, Detalle y Trazabilidad de Pedidos**

### Hitos Alcanzados
- **Directorio completo:** Lista paginada (20/página) con búsqueda full-text por nombre, documento, email o teléfono. Avatar con inicial, badge de tipo de documento, contador de pedidos y fecha de registro.
- **CRUD de Clientes:** Formulario unificado para crear y editar. Validación de documento único por tenant. Soporte para todos los tipos: DNI, RUC, CE, Pasaporte.
- **Detalle de cliente:** Cards de estadísticas (total pedidos, total gastado), tabla de historial de órdenes con columnas de productos, subtotal, IGV, total y estado.
- **Trazabilidad:** El nombre del cliente en la tabla de pedidos es ahora un enlace al detalle cuando existe el FK `order.client`.
- **PDF corregido:** El documento RUC/DNI en facturas/boletas ahora toma `order.client.document_number` y muestra el `document_type` dinámicamente.

### Added
- `client_list_view` — directorio con búsqueda y paginación; anotado con `order_count`
- `client_detail_view` — perfil con estadísticas agregadas e historial de pedidos
- `client_create_view` / `client_edit_view` — CRUD completo con validación
- `_client_form_context()` — helper compartido para formularios
- `templates/clients/client_list.html`, `client_detail.html`, `client_form.html`
- Sidebar: "Directorio Clientes" activado con highlight en `/clients/*`
- `seed_data.py` — 15 clientes por tenant con nombres peruanos, apellidos dobles, RUC empresarial (cada 5), documentos CE, y direcciones para el 70%

### Changed
- `orders/partials/order_row.html` — nombre del cliente enlaza a `web:client-detail` si existe `order.client`
- `reports/order_pdf.html` — label y número de documento dinámico desde `order.client`

### Fixed
- PDF: `order.customer_document` no existía en el modelo → usa `order.client.document_number`

---

## [1.7.0] - 2026-04-22

**💳 Modal de Pago, Correcciones Críticas y CI/CD**

### Hitos Alcanzados
- **Modal de pago mejorado:** Comisión Niubiz/Izipay claramente marcada como costo absorbido por la empresa (no el cliente). Referencia obligatoria para métodos no-efectivo (CARD, TRANSFER, WALLET/Yape/Plin). Validación client-side con Alpine.js que bloquea el submit si la referencia está vacía o es solo espacios.
- **Delivery en PDF:** La fila de envío aparece en el bloque de totales de la factura/boleta cuando `shipping_fee > 0`, de modo que el monto del documento coincide con el cobrado.
- **CI/CD restaurado:** `DJANGO_SETTINGS_MODULE` en el workflow apuntaba a `config.settings` (archivo vacío) en lugar de `config.settings.testing`. Tests de CI también fallaban porque `testing.py` heredaba la caché Redis de `base.py`; corregido con `LocMemCache`.
- **Suite de tests estabilizada:** 12 tests fallaban con 401/302 tras implementar autenticación. Añadidos fixtures `admin_user`, `auth_api_client`, `logged_in_client` en `conftest.py`; todos los tests actualizados.

### Added
- `conftest.py` — fixtures `admin_user`, `auth_api_client`, `logged_in_client`
- `seed_data.py` — `_generate_reference(method)`: referencias bancarias realistas (CARD: 12 dígitos, TRANSFER: 10–14 dígitos, WALLET: 9 dígitos), preservando ceros iniciales como strings

### Changed
- `pay_modal.html` — validación Alpine de referencia, wording de comisión, campo de referencia para Yape/Plin, `pointer-events-none` en htmx-indicator
- `reports/order_pdf.html` — fila de envío en bloque de totales y dirección de entrega en datos del cliente
- `seed_data.py` — órdenes con variedad de `delivery_type` (1/3 delivery), `shipping_fee` y `transaction_reference`

### Fixed
- `pay_modal.html` — botón confirmar no clickeable por `absolute inset-0` en el spinner de HTMX
- `.github/workflows/ci.yml` — `DJANGO_SETTINGS_MODULE: config.settings.testing`
- `config/settings/testing.py` — `CACHES` con `LocMemCache` (sin Redis en CI)
- `views.py` `order_create_view` — `TypeError: unsupported operand type(s) for /: 'float' and 'decimal.Decimal'` (precio era `float`, subtotal debía ser `Decimal`)
- `order_form.html` — fee de envío no se sumaba al total; corregido con `DEFAULT_SHIPPING_FEE` JS y `$watch('deliveryType')`

---

## [1.6.0] - 2026-04-19

**🖥️ Web Dashboard — Autenticación por Sesión, Máquina de Estados y Delivery**

### Hitos Alcanzados
- **Autenticación Web:** Login por sesión Django independiente de JWT. Decorator `tenant_access_required` valida slug de URL vs. organización del usuario. Página de login con diseño Tailwind por tenant.
- **Máquina de Estados de Órdenes:** Transiciones contextuales desde la tabla de pedidos vía modales HTMX: DRAFT→PENDING→PAID→SHIPPED→DELIVERED→COMPLETED, con ramas COURTESY y RETURNED. Botón de anulación disponible en estados pre-entrega.
- **Tipo de Entrega & Envío:** Campo `delivery_type` (PICKUP/DELIVERY) y `shipping_fee` por orden. Configuración de tarifa base por organización en Settings. Formulario de creación calcula el total incluyendo el fee en tiempo real.
- **Modal de Pago:** Vista dedicada con selección de método (EFECTIVO/CARD/TRANSFER/WALLET), cálculo de comisión y registro de `Payment`.

### Added
- `order_list_view` con búsqueda, filtro por estado y paginación
- `order_pay_modal_view` y `order_status_modal_view` — modales HTMX para transiciones
- `order_change_status_view` — actualización in-place de fila con OOB swap
- `settings_shipping_partial` — configuración de tarifa de envío por tenant
- `orders/partials/pay_modal.html`, `status_confirm_modal.html`
- Decorator `tenant_access_required` en `src/interfaces/web/decorators.py`
- `auth/login.html` — página de login con colores del tenant

### Changed
- `order_row.html` — botones de transición contextuales según estado actual
- `order_form.html` — selector de tipo de entrega con cálculo reactivo Alpine.js

---

## [1.5.0] - 2026-04-19

**📅 Seguridad Base, Modelo de Usuario y Autenticación JWT**

### Hitos Alcanzados
- **Settings por Entorno (P1-03):** El monolítico `config/settings.py` fue dividido en `base.py`, `local.py`, `testing.py` y `production.py`. Cada entorno tiene sus propias configuraciones de `DEBUG`, `ALLOWED_HOSTS` y `EMAIL_BACKEND`. Referencias actualizadas en `manage.py`, `wsgi.py`, `asgi.py`, `celery.py`, `docker-compose.yml` y `pytest.ini`.
- **ALLOWED_HOSTS Restrictivo (P1-02):** Eliminado el comodín `'*'`. Cada entorno declara sus hosts válidos; producción los lee desde la variable de entorno `ALLOWED_HOSTS`.
- **Modelo CustomUser:** Creado `src/domain/models/users.py` con `CustomUser(AbstractUser)` que usa email como identificador único (sin campo `username`), FK a `Organization` (nullable para superusuarios) y roles `ADMIN / STAFF / VIEWER`. `AUTH_USER_MODEL = 'domain.CustomUser'` configurado en `base.py`. Migración generada y superusuario de prueba verificado en base de datos.
- **Autenticación JWT (P1-01):** Integrado `djangorestframework-simplejwt`. Endpoints de login, refresh y verify disponibles. El token incluye claims del tenant (`email`, `role`, `organization_id`). `TenantViewMixin` reemplaza el uso de thread-local en todos los ViewSets de la API — la organización se deriva de `request.user` con soporte especial para superusuarios via `X-Org-ID`.

### Added
- `config/settings/base.py` — configuración común, `SIMPLE_JWT`, `AUTH_USER_MODEL`
- `config/settings/local.py` — desarrollo local
- `config/settings/testing.py` — suite de pruebas con hasher rápido y Celery eager
- `config/settings/production.py` — producción con SMTP y headers HTTPS
- `src/domain/models/users.py` — `CustomUser`, `CustomUserManager`, `UserRole`
- `POST /api/v1/auth/token/` — login con email + password → JWT
- `POST /api/v1/auth/token/refresh/` — renovación de access token
- `POST /api/v1/auth/token/verify/` — verificación de token
- `CustomTokenObtainPairView` y `CustomTokenObtainPairSerializer` con claims de tenant
- `TenantViewMixin` — mixin reutilizable para resolución de tenant en ViewSets
- `postman/nexus_oms_collection.json` — colección completa de pruebas de API con variables y scripts automáticos

### Changed
- Todos los ViewSets de API usan `request.user.organization` en lugar del thread-local
- `config/urls.py` — Swagger accesible sin auth (`AllowAny`) para facilitar desarrollo
- `requirements.txt` convertido de UTF-16 a UTF-8 estándar
- `src/domain/models/__init__.py` — exporta `CustomUser` y `UserRole`

### Fixed
- Conflicto de módulo vs paquete Python entre `config/settings.py` y `config/settings/` (eliminado el archivo monolítico)

**Estado de Cobertura:** 83% Total (Pytest-cov).

---

### 📅 Ajustes del 21 de Marzo, 2026
**Hitos Alcanzados:**
- **Arquitectura de Notificaciones:** Implementación del Patrón Strategy para envíos multi-canal (Email, Telegram, WhatsApp) desacoplados de la lógica de negocio.
- **Dashboard de Configuración:** Interfaz funcional para Tenants usando **HTMX** y **Tailwind CSS**, permitiendo persistencia de preferencias por organización.
- **Refactorización de Tareas:** Optimización de `tasks.py` con manejo de transacciones atómicas, zonas horarias (aware dates) y eliminación de duplicidad de código (DRY).
- **Validación de Integración:** Pruebas exitosas en entorno Docker confirmando el flujo completo: Configuración -> Tarea Celery -> Notificación.

**Estado de Cobertura:** 80% Total (Pytest-cov).

---

### [1.2.0] - 2026-03-22
**📅 Hitos de Estabilización y Arquitectura**
- Modularización del Dominio (DDD): Fractura de la capa `domain` en sub-paquetes especializados (`models/`, `services/`, `tasks/`), eliminando dependencias circulares y mejorando la cohesión (SRP).

- Capa de Finanzas: Implementación de `FinanceService` para cálculos centralizados de margen neto y rentabilidad, integrando pagos y órdenes de compra.

- Robustez de Tests: Resolución de errores críticos de integridad de datos (`NotNullViolation` en `Stock`) y esquemas de modelos (`Payment` fields).

- Optimización de Mocks: Actualización de rutas de parcheo para tareas de Celery, garantizando tests unitarios verdaderamente aislados.

### Added
- `FinanceService` : Lógica para cálculo de profit margin y net income.

- Fixtures globales en `conftest.py` para `warehouse` y `supplier`.

- Soporte para métodos de pago (`CARD`, etc.) en la creación de transacciones.

### Changed
- Refactorización Mayor: Migración de lógica plana en `domain/` a estructura de paquetes.

- Mejora en `OrderService.create_order`: Validación estricta de existencias antes de la creación de la orden.

- Actualización de `mocker.patch` en todos los tests para reflejar la nueva ubicación de las tareas.

### Fixed
- `ModuleNotFoundError` tras la reestructuración de carpetas.

- `IntegrityError` en el modelo `Stock` al faltar la referencia obligatoria a `Warehouse`.

- `TypeError` en instanciación de `Payment` por argumentos inesperados.


---

### [1.3.0] - 2026-04-05

**📅 Hitos de Interfaz de Usuario y Gestión de Ventas**
- **Arquitectura de Panel (Layout Modular):** Reestructuración del `base.html` para soportar un Sidebar de navegación lateral y un Navbar persistente, transformando la experiencia de usuario en un entorno ERP profesional.
- **Flujo de Órdenes Completo:** Implementación de la vista de listado de órdenes con soporte para búsqueda, filtrado por estado y paginación (Paginator de Django).
- **Interactividad HTMX:** Integración de un contenedor global de modales (`#modals-here`) para previsualizaciones rápidas de detalles de pedidos sin recarga de página.
- **Política de Integridad de Datos:** Sustitución de la eliminación física por "Borrado Lógico" (`CANCELLED`), asegurando la trazabilidad financiera y auditoría de ventas.

### Added

- `order_list_view`: Vista principal para la gestión histórica de pedidos por organización.
- `order_cancel_view`: Lógica para la anulación segura de pedidos con actualización de estado.
- `layouts/partials/sidebar.html`: Menú lateral dinámico con agrupaciones lógicas (Ventas, Inventario, Finanzas).
- `layouts/partials/navbar.html`: Barra superior modular con identidad corporativa del Tenant y menú de usuario (Alpine.js).
- `orders/partials/order_row.html`: Fragmento especializado para renderizado individual de filas con soporte para estados visuales (tachado en cancelaciones).

### Changed

- **Refactorización de Layout:** Migración de diseño centrado a estructura de grid con Sidebar fijo y Main content responsivo.
- **UX de Órdenes:** Los botones de acción ahora utilizan `hx-target` específicos (`closest tr` para anulaciones, `#modals-here` para detalles) mejorando la fluidez de la interfaz.
- **Rutas Web:** Unificación de nombres de URL para mayor consistencia (`order-list`, `order-create`, `order-cancel`).

### Fixed

- `NoReverseMatch`: Resolución de errores en plantillas al referenciar rutas de eliminación/anulación inexistentes.
- **Inyección de Fragmentos:** Corrección de error de UI donde los parciales de HTMX se incrustaban dentro de la tabla en lugar de disparar modales.
- **CSS dinámico:** Ajuste en la configuración de Tailwind para asegurar que los colores del Tenant se apliquen correctamente a los nuevos componentes del Sidebar.

**Estado de Cobertura:** 86% Total (Pytest-cov) 🚀.

### [1.4.0] - 2026-04-11

**📅 Hitos de Finanzas, Búsqueda Reactiva y Sincronización Global**
- **Motor de Búsqueda de Productos (UX):** Implementación de búsqueda asíncrona mediante HTMX en el formulario de ventas, permitiendo filtrado dinámico por Nombre/SKU con optimización de QuerySets (`annotate` para stock total).
- **Integración con APIMigo:** Automatización de la sincronización de tipos de cambio (USD/PEN) mediante servicios especializados y fallback robusto en caso de fallos de API externa.
- **Consistencia Cronológica (Fix Crítico):** Sincronización total de zonas horarias entre Docker, PostgreSQL y Django (`America/Lima`), eliminando el desfase de fechas en registros financieros.
- **Dashboard de Histórico:** Creación del módulo de auditoría de tipos de cambio con soporte de paginación y trazabilidad de origen de datos (APIMigo vs Manual).

### Added
- `ExchangeService`: Lógica centralizada para recuperación y persistencia de tasas de cambio.
- `exchange_history_view`: Vista dedicada para la visualización del histórico de fluctuación de divisas.
- `finance/exchange_history.html`: Template con diseño profesional para auditoría de tasas de cambio.
- Navbar Links: Acceso directo desde la UI principal al historial financiero mediante el componente de tipo de cambio.

### Changed
- **Optimización de UI de Órdenes:** Refuerzo visual en inputs de "Documento" y "Búsqueda" mediante el uso de bordes basados en el color secundario del Tenant para mejorar la detectabilidad.
- **Refactorización de Búsqueda:** Migración de filtros pesados a lógica de base de datos para evitar latencia en la selección de productos.
- **Docker Orchestration:** Actualización de `docker-compose.yml` con healthchecks de servicios y sincronización forzada de `TZ` (America/Lima).

### Fixed
- `FieldError` en `search_product_partial`: Corrección de ordenamiento por campos inexistentes (`created_at`) en el modelo `Product`.
- `FieldError` en `ExchangeRate`: Eliminación de filtrado por `organization` en modelos de datos globales/financieros.
- **UTC Date Drift:** Resolución del error que registraba transacciones con fecha del día siguiente debido al desfase horario del servidor.
- **HTMX Trigger Fix:** Ajuste de disparadores (`keyup changed`) para evitar múltiples peticiones innecesarias al backend.

**Estado de Cobertura:** 88% Total (Pytest-cov) 🚀.

---

## [2026-04-18] - Refactorización de Pruebas y Monitoreo de Tareas

### Añadido
- Integración de **Celery Beat** en la infraestructura Docker para la orquestación de tareas programadas (reportes diarios/mensuales).
- Integración de **Flower** para el monitoreo en tiempo real de workers y flujo de tareas en el puerto `5555`.
- Tests de integración para `reporting_tasks` incluyendo generación de PDF con WeasyPrint y manejo de caché.
- Tests para el flujo de alertas en `notification_tasks` (Telegram/WhatsApp).

### Corregido
- **Bug Crítico:** Corregido `NameError: name 'Q' is not defined` en `search_product_partial` dentro de `web.views`.
- Corregido `IntegrityError` en modelos de Devolución al estandarizar campos obligatorios en el entorno de pruebas.
- Ajustada firma del método `process_return` en `OrderService` para soportar parámetros de organización y notas.

### Mejorado
- El **Coverage Global** del proyecto subió del **77% al 83%**.
- Se optimizó el tiempo de ejecución de las pruebas de notificación reduciendo los `time.sleep` en entorno de test.
- Mejora en la estabilidad del middleware de Multitenancy bajo condiciones de test de integración.

---
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
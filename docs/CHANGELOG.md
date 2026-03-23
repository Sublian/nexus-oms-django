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
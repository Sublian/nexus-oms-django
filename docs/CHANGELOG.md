### 📅 Ajustes del 21 de Marzo, 2026
**Hitos Alcanzados:**
- **Arquitectura de Notificaciones:** Implementación del Patrón Strategy para envíos multi-canal (Email, Telegram, WhatsApp) desacoplados de la lógica de negocio.
- **Dashboard de Configuración:** Interfaz funcional para Tenants usando **HTMX** y **Tailwind CSS**, permitiendo persistencia de preferencias por organización.
- **Refactorización de Tareas:** Optimización de `tasks.py` con manejo de transacciones atómicas, zonas horarias (aware dates) y eliminación de duplicidad de código (DRY).
- **Validación de Integración:** Pruebas exitosas en entorno Docker confirmando el flujo completo: Configuración -> Tarea Celery -> Notificación.

**Estado de Cobertura:** 80% Total (Pytest-cov).

---

## 📅 Ajustes del 22 de Marzo, 2026
### Added
- New `FinanceService` for centralized net margin and profitability calculations.
- Integrated `Payment` and `PurchaseOrder` logic into financial reporting.
- Added missing test fixtures for `warehouse` and `supplier` in `conftest.py`.

### Changed
- **Major Architecture Refactor**: Modularized `domain` layer into sub-packages (`models/`, `services/`, `tasks/`).
- Resolved circular dependency between `OrderService` and `tasks` by implementing absolute imports and lazy loading.
- Improved `OrderService.create_order` to strictly validate stock levels before processing.

### Fixed
- Fixed `ModuleNotFoundError` in task execution post-refactor.
- Corrected `Payment` instantiation in tests by using the correct schema (`method='CARD'`).
- Resolved `IntegrityError` in stock testing by ensuring `warehouse_id` is always present.
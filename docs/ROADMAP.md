# 🗺️ Nexus Project Roadmap

Este documento detalla los hitos de desarrollo y los objetivos técnicos del proyecto.  
Es la **fuente de verdad** sobre qué está hecho y qué falta por implementar.

---

## Hito 1: Cimientos y Multi-tenancy 🏗️ (COMPLETADO ✅)

**Objetivo**: Tener una base sólida del proyecto con arquitectura definida, entorno listo y soporte multi-tenant a nivel técnico.

- [x] Definición de arquitectura y diagramas (limpia/hexagonal + DDD ligero).
- [x] Configuración básica del proyecto Django (settings, apps, estructura de `src/`).
- [x] Configuración de Docker (Postgres, Redis, Celery).
- [x] Middleware de aislamiento de datos por organización/tenant.
- [x] Modelo de Organización (Tenants).
- [x] Script de carga inicial de datos (Seeder).

---

## Hito 2: Core de Catálogo e Inventario 📦 (COMPLETADO ✅)

**Objetivo**: Modelar el núcleo de productos e inventario, con lógica de impuestos por organización y base para el OMS.

- [x] Modelos de Producto, Categoría, Bodega y Stock.
- [x] Lógica de impuestos configurable por Organización/Tenant.
- [x] Endpoints de API para Catálogo e Inventario (crud funcional).
- [x] Pruebas de validación de stock vía API (unitarias + integración).
- [x] Validación de que todas las consultas respeten el contexto de tenant.
- [x] Testing Suite (Pytest): Fixtures para Organization, Warehouse y Supplier.
- [x] Stock Logic Tests: Integridad referencial (Warehouse-Stock) y persistencia.

---

## Hito 3: Gestión de Pedidos y Logística Inversa 🧾 (COMPLETADO ✅ — Refactorizado)

**Objetivo**: Implementar el flujo principal de órdenes (Order Management System).

- [x] Modelos de Order, OrderItem y OrderReturn.
- [x] Servicio de dominio para cálculo de totales, descuentos e impuestos.
- [x] Endpoints de creación de pedidos (POST).
- [x] Blindaje de Devoluciones: Validación de techo de devolución y stock dinámico.
- [x] Pruebas de integración de flujo completo (Venta -> Retorno -> Reposición de Stock).
- [x] **Domain Unit Tests**: Cobertura del 91% en OrderService y 96% en modelos de venta.
- [x] **FinanceService**: Motor de cálculo para márgenes netos y rentabilidad.

---

## Hito 4: Reactividad y Procesos Asíncronos - Celery & Redis ⚡ (COMPLETADO ✅)

**Objetivo**: Soportar procesos de larga duración y asegurar la infraestructura de mensajería.

- [x] Capa de Caché con Redis: Optimización de reportes.
- [x] Integración de **Celery + Redis** para tareas de background.
- [x] **Mocker Pattern**: Mocks para tareas asíncronas en tests unitarios.
- [x] Configuración de Workers para procesamiento de señales de dominio.


---

## Hito 5: Interfaz de Usuario y Experiencia Reactiva (HTMX & Tailwind) 🎨 (EN PROGRESO)

**Objetivo**: Construir la capa visual del sistema enfocada en la eficiencia del operador del OMS, utilizando tecnologías modernas de renderizado parcial.

- [x] **Layout Base y Sistema de Navegación**: Estructura profesional con Sidebar lateral, Navbar modular y persistencia de identidad visual por Tenant.
- [x] **Arquitectura de Modales Globales**: Implementación de contenedor `#modals-here` para carga dinámica de detalles y formularios mediante HTMX.
- [x] **Gestión de Órdenes en UI**: Listado reactivo de pedidos con estados visuales y acciones integradas.
- [x] **Borrado Lógico (Cancelación) en UI**: Flujo de anulación de pedidos con feedback inmediato (tachado/deshabilitado) sin recarga de página.
- [ ] **Componentes de Búsqueda Avanzada**: Implementación de búsqueda en tiempo real de productos y filtrado de pedidos mediante `hx-trigger="keyup changed delay:500ms"`.
- [ ] **Feedback de Tareas Asíncronas**: Barras de progreso en tiempo real conectadas a Celery mediante Polling de HTMX para generación de reportes pesados.
- [ ] **Validación Inline**: Feedback inmediato en formularios de creación de órdenes para evitar errores de servidor.
- [ ] **Data Tables Pro**: Listados de productos y stock con paginación, ordenamiento dinámico y edición rápida en línea.

**Resultado esperado**:  
Una consola de administración fluida donde el usuario gestiona el ciclo de vida de las órdenes con tiempos de respuesta mínimos, emulando la agilidad de una SPA.

---

## Hito 6: El Toque Senior (Observabilidad, Cloud & CD) 🐱‍💻 (EN PROGRESO)

**Objetivo**: Llevar el proyecto a un estándar de producción: observabilidad, nube y despliegue automatizado en AWS.

- [x] Documentación interactiva de la API con **Swagger / drf-spectacular**.
- [x] **High-Quality Coverage**: Alcanzado el **86% de cobertura total**.
- [x] **Setup de CI/CD (GitHub Actions)**: Automatización de tests y Codecov.
- [x] **Cloud Ready**: Configuración de instancia **AWS EC2 (Ubuntu + Nginx)**.
- [ ] **Deployment Automático (CD)**: Despliegue continuo hacia AWS mediante GitHub Actions.
- [ ] **Audit Logs**: Historial de movimientos por pedido/entidad (Trazabilidad total).
- [ ] **Mailing System**: Notificaciones de reportes y alertas de stock bajo (Integración con SendGrid/Amazon SES).
- [ ] **Hardening de Seguridad**: SSL/TLS (Certbot) y Rate limiting por Org-ID a nivel de Nginx.

---

## Notas de Versión

### v0.40 - "The ERP Experience" (Actual)
- **UI Architecture**: Transición a un layout profesional de tres capas (Navbar, Sidebar, Content).
- **HTMX Integration**: Implementación de carga parcial de componentes y gestión de modales para el flujo de órdenes.
- **Data Integrity**: Refuerzo del borrado lógico en la capa visual para cumplir con estándares de auditoría.

### v0.30 - "The Modular Leap"
- **Arquitectura Limpia**: Transición de dominio monolítico a sub-paquetes (`models`, `services`, `tasks`).
- **Precisión Financiera**: Integración de `Payment` con `FinanceService` para reportes de rentabilidad real (Net Margin).
- **Resiliencia**: CI/CD configurado con cobertura dinámica y resolución de importaciones circulares.

---

## Cómo leer este Roadmap

- Si eres reviewer de **arquitectura**: Revisa Hito 1, 2 y 3.
- Si te interesa la parte **Frontend/UX Senior**: Enfócate en el Hito 5 (HTMX, Tailwind, AlpineJS).
- Si te interesa la parte **DevOps / Cloud**: Enfócate en Hito 6 (GitHub Actions, AWS EC2, Seguridad).
# Nexus OMS — Resumen de Avances del Proyecto
**Fecha de corte:** 26 de Abril, 2026 (v2.0.0)

---

## Estado General

| Módulo | Estado |
|--------|--------|
| Infraestructura & Multi-tenancy | ✅ Completo |
| API REST (DRF + JWT) | ✅ Completo |
| Web Dashboard (HTMX) | ✅ En producción |
| Autenticación Web + JWT | ✅ Completo |
| Gestión de Órdenes (Block 1) | ✅ **Completamente funcional** |
| Edit inline de items | ✅ Completo con validación de stock |
| Delete items + auto-cancelación | ✅ Completo con nota obligatoria |
| Directorio de Clientes | ✅ Completo |
| Gestión de Productos & SKUs | ✅ Completo |
| CI/CD (GitHub Actions) | ✅ Estable |
| Cobertura de tests | ✅ 91% (61 tests passing) |

---

## Lo que se ha construido

### 🏗️ Base & Infraestructura
- **Multi-tenancy completo:** `TenantModel` + `TenantManager` con thread-local `organization_id`. Toda query filtra automáticamente por tenant; no hay filtrado manual en vistas.
- **Settings por entorno:** `base.py` / `local.py` / `testing.py` / `production.py`. CI usa `testing.py` con `LocMemCache` (sin Redis necesario).
- **Docker Compose:** Servicios: `web` (Django), `db` (PostgreSQL), `redis`, `celery` worker, `celery-beat`, `flower` (monitoreo en `:5555`).
- **Arquitectura Clean/DDD:** Capas `domain/` → `application/` → `infrastructure/` → `interfaces/api` + `interfaces/web`.

### 🔐 Autenticación Dual
- **API:** JWT via `djangorestframework-simplejwt`. Claims incluyen `email`, `role`, `organization_id`. Tokens: acceso 1h, refresh 7 días.
- **Web:** Sesión Django. Decorator `tenant_access_required` valida que el slug de URL corresponda a la organización del usuario.
- **Modelo CustomUser:** Email como identificador, FK a `Organization`, roles `ADMIN/STAFF/VIEWER`.

### 📦 Gestión de Órdenes (Block 1 ✅)
- **Ciclo de vida completo:** `DRAFT → PENDING → PAID → SHIPPED → DELIVERED → COMPLETED`, con ramas `COURTESY` (cortesía) y `RETURNED` (devolución). Anulación (`CANCELLED`) disponible en estados pre-entrega.
- **Tipo de entrega:** `PICKUP` (retiro en tienda) o `DELIVERY` (con `delivery_address` y `shipping_fee`). Tarifa configurable por organización en Settings. Ahora visible en modal de detalle.
- **Modal de pago:** Selección de método (EFECTIVO / CARD / TRANSFER / WALLET). Comisión bancaria (3.5%) absorbida por la empresa. Referencia obligatoria para métodos no-efectivo con validación client-side. Valida stock antes de PAID.
- **PDF/Factura:** Diseño estilo SUNAT. Muestra RUC/DNI del cliente, fee de envío en totales, dirección de entrega, QR, monto en letras.
- **Tabla de pedidos:** Búsqueda full-text, filtro por estado, paginación, modales HTMX para ver detalle y gestionar transiciones desde la misma fila.
- **Edit inline de items:** Pencil icon en modal de detalle permite editar cantidad en DRAFT/PENDING. Valida stock, recalcula totales automático. Solo items+totales se actualizan (partial modal refresh).
- **Delete de items:** Trash icon con confirmación. Si es último item: requiere nota obligatoria, auto-cancela orden, restaura stock, pone totales en 0. Si hay más items: recalcula totales sin cancelar.
- **Control de inventario:** Stock se decrementa al crear orden (DRAFT), se restaura al cancelar. Signal con `select_for_update()` asegura atomicidad.

### 👥 Directorio de Clientes
- **Lista:** Búsqueda por nombre, documento, email o teléfono. Paginación (20/página). Columnas: avatar con inicial, tipo + número de documento, contacto, conteo de pedidos, fecha de registro.
- **CRUD:** Crear y editar. Tipos de documento: DNI, RUC, CE, Pasaporte. Validación de unicidad por tenant. Nombre en mayúsculas automático.
- **Detalle:** Stats (total pedidos, total gastado), historial de órdenes con subtotal, IGV, total y estado.
- **Trazabilidad:** El nombre del cliente en la tabla de pedidos enlaza directo a su perfil cuando está registrado.

### 🏷️ Gestión de Productos & SKUs
- **Lista:** Búsqueda por nombre/SKU/descripción. Tabs de estado (Activos/Suspendidos/Todos). Filtro por categoría. Badges de stock con color (rojo=sin stock, ámbar=crítico, verde=ok).
- **CRUD:** Crear y editar. SKU único por tenant (convertido a mayúsculas). Categoría con find-or-create. Stock inicial opcional al crear (almacén + cantidad).
- **Suspensión:** Toggle activo/inactivo vía un botón en el detalle; no hay borrado físico.
- **Detalle:** Info del producto, stock por almacén con fecha de actualización, tabla de trazabilidad de pedidos (cantidad vendida y subtotal por orden).

### 🔄 Tareas Asíncronas (Celery)
- `generate_weekly_all_orgs` — Lunes 00:00 UTC: genera PDF de reporte semanal por tenant.
- `sync_daily_exchange_rate` — Diario 06:00 UTC: sincroniza tipo de cambio USD/PEN vía APIMigo.
- En tests: `CELERY_TASK_ALWAYS_EAGER=True` (síncrono).

### 🧪 Suite de Tests
- **53 tests pasando** (0 fallos).
- Fixtures clave: `admin_user`, `auth_api_client` (JWT), `logged_in_client` (sesión).
- Tests de API usan `force_authenticate`; tests web usan `force_login`.
- CI: GitHub Actions con `DJANGO_SETTINGS_MODULE=config.settings.testing`.

---

## Pendientes Priorizados

### Alta prioridad
| ID | Descripción | Status |
|----|-------------|--------|
| P1-04 | Validar `MIGO_API_TOKEN` al arranque del servidor | ⏳ Pendiente |
| P2-06 | Cobertura de tests: 91% (Block 1 tests completos) | ✅ Avanzado |

### Media prioridad
| ID | Descripción | Status |
|----|-------------|--------|
| P2-01 | Logging estructurado (JSON) en `base.py` | ⏳ Pendiente |
| P2-02 | Manejo de `DoesNotExist` en middleware de multitenancy | ⏳ Pendiente |
| P3-01 | Paginación en endpoints DRF (`/api/v1/orders/`, `/api/v1/products/`) | ⏳ Pendiente |
| P3-02 | Rate limiting en la API (throttling) | ⏳ Pendiente |

### Roadmap Block 2-4
| Bloque | Descripción | Status |
|--------|-------------|--------|
| **Block 1** | Order lifecycle + inventory mgmt | ✅ **DONE** |
| **Block 2** | Notificaciones (email, Telegram, WhatsApp) | ⏳ Próximo |
| **Block 3** | Búsqueda de productos refinada | ⏳ Después |
| **Block 4** | UI/UX polish (toasts, spinners, dashboard metrics) | ⏳ Después |

### Deuda técnica (RESUELTO)
- ✅ `order_detail_modal.html` ahora muestra `delivery_type` (badge) y `shipping_fee` (fila en totales)
- ✅ Control de inventario automático: stock se decrementa en DRAFT, se restaura si se cancela
- ✅ Edit inline de items con validación de stock
- ✅ Delete de items con restauración de stock y auto-cancelación si orden queda vacía

---

## Stack Tecnológico

| Capa | Tecnología |
|------|------------|
| Backend | Django 4.x + DRF + django-fsm |
| Auth | SimpleJWT + Django sessions |
| Base de datos | PostgreSQL |
| Cache / Broker | Redis |
| Tareas async | Celery + Celery Beat |
| Monitoreo tareas | Flower |
| Frontend | HTMX + Alpine.js + Tailwind CSS (CDN) |
| PDF | WeasyPrint |
| Pagos | APIMigo (gateway peruano) |
| Contenedores | Docker + Docker Compose |
| CI/CD | GitHub Actions |

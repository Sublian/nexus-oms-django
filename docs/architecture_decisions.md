# 🧠 Decisiones Arquitectónicas y de Diseño - Nexus OMS

Este documento registra las justificaciones técnicas, evolución de la infraestructura y aprendizajes clave durante el desarrollo de **Nexus OMS**, sirviendo como la "Verdad Única" para el mantenimiento y escalabilidad del sistema.

## 🏛️ Decisiones de Diseño y Evolución

### 1. Arquitectura Multi-tenant (Aislamiento de Datos)
- **Decisión:** Implementar aislamiento mediante `organization_id` a nivel de aplicación (Shared Database).
- **Justificación:** Se priorizó un despliegue ágil y costos contenidos. El aislamiento se garantiza mediante **Custom Managers** de Django que filtran automáticamente por el contexto del Tenant actual, evitando fugas de datos entre organizaciones.

### 2. UI Modular y Patrón de Panel (Sidebar + Navbar)
- **Decisión:** Implementar un layout de tres capas (Navbar superior fijo, Sidebar lateral de navegación y Área de contenido dinámico).
- **Justificación:** Para transformar la aplicación de una "herramienta de una sola página" a un **ERP Profesional**. La separación del Navbar (Gestión de Sesión) y Sidebar (Navegación de Módulos) permite una expansión orgánica de funcionalidades como Inventario, Stock y Finanzas sin saturar la interfaz.

### 3. Interactividad con HTMX y Contenedores de Modales Globales
- **Decisión:** Uso de un contenedor único `<div id="modals-here"></div>` en el `base.html`.
- **Justificación:** Evita la "inyección incrustada" de fragmentos HTML dentro del flujo de la página. Al definir un objetivo (target) global, los detalles de órdenes y formularios de creación se renderizan como capas superiores (Overlays), manteniendo limpia la estructura del DOM principal.

### 4. Gestión de Estado: Borrado Lógico (Idempotencia Financiera)
- **Decisión:** Sustituir la eliminación física de registros por el estado `CANCELLED` (Borrado Lógico) en el modelo `Order`.
- **Justificación:** En sistemas contables y ERPs, la eliminación de datos rompe la trazabilidad y las secuencias de auditoría. Cambiar el estado permite:
    - Mantener el historial de intentos de venta.
    - Visualizar registros anulados (con estilo *line-through* en UI).
    - Evitar errores de integridad referencial en reportes financieros.

### 5. Adopción de Patrones de Diseño (SOLID)
- **Strategy:** El sistema de reportes es agnóstico al canal (Email, PDF).
- **Service Layer (SRP):** La lógica reside en `services/`, evitando "Fat Models".
- **Open/Closed:** El sistema permite añadir nuevos métodos de pago o estados de orden sin modificar el núcleo del dominio.

### 6. Settings por Entorno (ADR-006)
- **Decisión:** Dividir `config/settings.py` en un paquete `config/settings/` con cuatro módulos: `base`, `local`, `testing`, `production`.
- **Justificación:** Un único settings file con `DEBUG=True` y `EMAIL_BACKEND=console` puede filtrarse accidentalmente a producción. La separación fuerza que cada entorno declare explícitamente sus overrides, elimina la posibilidad de `ALLOWED_HOSTS = ['*']` en producción, y permite que `pytest.ini` apunte directamente a `config.settings.testing` sin variables de entorno adicionales.
- **Consecuencia:** `DJANGO_SETTINGS_MODULE` debe configurarse en `docker-compose.yml`, `Dockerfile` de producción y CI. El valor default en `manage.py`, `wsgi.py` y `celery.py` apunta a `local`.

### 7. Modelo CustomUser con Email como Identificador (ADR-007)
- **Decisión:** Crear `CustomUser(AbstractUser)` que elimina el campo `username` y usa `email` como `USERNAME_FIELD`. El modelo incluye FK a `Organization` (nullable para superusuarios) y un campo `role` con tres niveles: `ADMIN`, `STAFF`, `VIEWER`.
- **Justificación:** El MVP no tenía modelo de usuario propio, usando el `auth.User` de Django sin personalización. Esto impedía implementar autenticación por tenant (un usuario debe pertenecer a una organización) y diferenciación de permisos por rol. Usar email como identificador es el estándar moderno de B2B SaaS; evita colisiones de username entre tenants.
- **Consecuencia:** Requirió borrar y regenerar migraciones. Los superusuarios tienen `organization=None` — son administradores centrales sin tenant. El `CustomUserManager` implementa `create_user` y `create_superuser` compatibles con `manage.py createsuperuser`.

### 8. Autenticación JWT para la API (ADR-008)
- **Decisión:** Usar `djangorestframework-simplejwt` con tokens Bearer para proteger todos los endpoints DRF. El token embebe `email`, `role` y `organization_id` como claims adicionales.
- **Justificación:** La API anterior era accesible con solo el header `X-Org-ID`, sin ninguna verificación de identidad. Cualquier actor que conociera un UUID de organización podía leer y escribir datos de ese tenant. JWT resuelve esto vinculando la sesión API al `CustomUser` autenticado. Se eligió JWT sobre Session Auth porque la API debe ser consumible por clientes externos (mobile, CLI, Postman) sin depender de cookies.
- **Consecuencia:** La capa web (HTMX) mantiene el middleware de slug para resolución de tenant — no usa JWT, por lo que las vistas web no requieren autenticación en el MVP. El Swagger (`/api/docs/`) se configuró con `AllowAny` para facilitar el desarrollo. Los superusuarios conservan acceso cross-tenant via header `X-Org-ID`.
- **`TenantViewMixin`:** Mixin reutilizable en todos los ViewSets que resuelve `organization` desde `request.user.organization`, eliminando la dependencia del thread-local en la capa de API.

---

# 🎓 Lecciones Aprendidas y Mejores Prácticas

## 🔄 Resolución de Dependencias Circulares (ADR 003)
**Aprendizaje:** El crecimiento del ERP generó archivos "God" en `domain/`. La solución fue fracturar la capa de dominio en: `models/` (Persistencia), `services/` (Orquestación) y `tasks/` (Asíncrono). El uso de **Lazy Loading** en métodos específicos asegura que los modelos estén cargados antes que las tareas de Celery.

## ⚡ UX con HTMX: `hx-target` y `closest`
**Aprendizaje:** Al realizar acciones sobre tablas (como anular una fila), el uso de `hx-target="closest tr"` permite actualizar solo el fragmento necesario. Esto reduce la carga del servidor y elimina el "parpadeo" de la página, ofreciendo una experiencia similar a una Single Page Application (SPA) pero manteniendo la simplicidad de Django.

## 🛠️ Gestión de Contexto en Tareas Asíncronas
**Aprendizaje:** Se debe serializar y pasar explícitamente el `organization_id` a las tareas de Celery. Esto garantiza que el worker opere siempre bajo el marco de seguridad del Tenant correcto, manteniendo el aislamiento multi-tenant incluso fuera del ciclo de solicitud HTTP.

---

## 📈 Estado de Calidad del Proyecto
- **Code Coverage:** 83% (en progreso hacia 90%).
- **Arquitectura:** Domain-Driven Design (DDD) modular con Clean Architecture.
- **Autenticación:** JWT con claims de tenant — `djangorestframework-simplejwt`.
- **Estándar de Código:** PEP8, principios SOLID y Clean Code.
- **Estado UI:** Layout 100% responsivo con Sidebar dinámico y soporte para Modales.
- **Seguridad API:** Todos los endpoints protegidos por `IsAuthenticated` + JWT.

---
*Última actualización: 19 de Abril de 2026 — Cierre de fase: Seguridad Base y Modelo de Usuario.*
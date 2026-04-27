# Plan de Mejoras — Nexus OMS

> **Última revisión:** 2026-04-26 (v2.0.0)  
> **Cobertura actual:** 91% (61 tests)  
> **Estado general:** Block 1 COMPLETADO · Order lifecycle + inventory management funcional · Próximo: Block 2 (Notificaciones)

---

## 🎯 HITO IMPORTANTE: Block 1 Completado (26 de Abril, 2026)

**Resumen v2.0.0:**
- ✅ Edit inline de items en órdenes (DRAFT/PENDING)
- ✅ Delete de items con validación y auto-cancelación
- ✅ Campo `nota` obligatorio al borrar último item
- ✅ Partial modal updates (solo items+totales se refrescan)
- ✅ Stock automation: decremento en creación, restauración en cancelación
- ✅ 61 tests passing (83% → 91% coverage)
- ✅ Todos bugs resueltos (double-decrement, modal vacío, transacciones)

**Próximo:** Block 2 (Notificaciones — Email/Telegram/WhatsApp) en planificación.

---

## Resumen Ejecutivo

El proyecto alcanzó un hito importante con Block 1 completamente funcional y testeado. Las prioridades críticas de seguridad (P1-01, P1-02, P1-03) fueron resueltas en abril 19. Block 1 (Order lifecycle) completado el 26 de abril. El foco ahora es Block 2 (Notificaciones) y luego refinamientos de UI/UX.

---

## ✅ Correcciones Completadas

| ID | Descripción | Fecha | Versión |
|----|-------------|-------|---------|
| — | `unique_together = ('organization', 'sku')` en Product | 2026-04-18 | v1.5.0-pre |
| — | Celery Beat en `docker-compose.yml` con volumen persistente | 2026-04-18 | v1.5.0-pre |
| — | Flower en `docker-compose.yml` (puerto 5555) | 2026-04-18 | v1.5.0-pre |
| — | `annotate(total_stock=Sum(...))` + import `Q` en búsqueda de productos | 2026-04-18 | v1.5.0-pre |
| — | Cobertura de pruebas > 80% | 2026-04-18 | v1.5.0-pre |
| **P1-03** | Settings divididos por entorno (`base/local/testing/production`) | 2026-04-19 | v1.5.0 |
| **P1-02** | `ALLOWED_HOSTS` restrictivo por entorno | 2026-04-19 | v1.5.0 |
| — | Modelo `CustomUser` con email como identificador y roles | 2026-04-19 | v1.5.0 |
| — | `AUTH_USER_MODEL = 'domain.CustomUser'` | 2026-04-19 | v1.5.0 |
| **P1-01** | Autenticación JWT (`djangorestframework-simplejwt`) | 2026-04-19 | v1.5.0 |
| — | `TenantViewMixin`: org derivada de `request.user` en API | 2026-04-19 | v1.5.0 |
| — | `requirements.txt` convertido a UTF-8 | 2026-04-19 | v1.5.0 |
| **P1-05** | Login web con sesiones Django + control de acceso por tenant | 2026-04-25 | v1.6.0 |
| — | `tenant_access_required` decorator en todas las vistas del dashboard | 2026-04-25 | v1.6.0 |
| — | `seed_data` genera usuarios admin por organización + superuser global | 2026-04-25 | v1.6.0 |
| — | Logout con `hx-boost="false"` para evitar que HTMX intercepte la navegación | 2026-04-25 | v1.6.0 |
| — | Botón "Nuevo Pedido" unificado (`btn-tenant`, ícono SVG, texto) en dashboard y lista de pedidos | 2026-04-25 | v1.6.0 |
| **Block 1** | Fix: double-decrement bug en stock (líneas 293-294 removidas) | 2026-04-26 | v2.0.0 |
| **Block 1** | Feature: delivery_type + shipping_fee visible en modal de detalle | 2026-04-26 | v2.0.0 |
| **Block 1** | Feature: Edit inline de items con validación de stock (partial update HTMX OOB) | 2026-04-26 | v2.0.0 |
| **Block 1** | Feature: Delete de items con auto-cancelación si orden vacía (nota obligatoria) | 2026-04-26 | v2.0.0 |
| **Block 1** | Tests: 53 → 61 passing (edit, delete, empty order scenarios) | 2026-04-26 | v2.0.0 |
| **Block 1** | Migration: campo `nota` agregado al modelo Order | 2026-04-26 | v2.0.0 |

---

## PRIORIDAD 1 — Bloqueantes de Seguridad ✅ COMPLETADO

### ~~P1-01: Autenticación en la API REST~~ ✅ IMPLEMENTADO (2026-04-19)

**Implementación realizada:**
- `djangorestframework-simplejwt==5.4.0` agregado a `requirements.txt`
- `DEFAULT_AUTHENTICATION_CLASSES` y `DEFAULT_PERMISSION_CLASSES` configurados en `base.py`
- Endpoints: `POST /api/v1/auth/token/`, `/token/refresh/`, `/token/verify/`
- `CustomTokenObtainPairView` con claims de tenant (`email`, `role`, `organization_id`) en el JWT
- `TenantViewMixin` reemplaza el thread-local en todos los ViewSets de la API

---

### ~~P1-02: `ALLOWED_HOSTS` demasiado permisivo~~ ✅ IMPLEMENTADO (2026-04-19)

**Implementación realizada:**
- `local.py` → `['localhost', '127.0.0.1', '0.0.0.0']`
- `testing.py` → `['localhost', '127.0.0.1', 'testserver']`
- `production.py` → `env.list('ALLOWED_HOSTS')` (obligatorio en `.env`)

---

### ~~P1-03: Separar configuraciones por entorno~~ ✅ IMPLEMENTADO (2026-04-19)

**Implementación realizada:**
```
config/settings/
├── base.py        # Configuración común, AUTH_USER_MODEL, SIMPLE_JWT
├── local.py       # DEBUG=True, email a consola
├── testing.py     # CELERY_TASK_ALWAYS_EAGER=True, hasher rápido
└── production.py  # DEBUG=False, SMTP, headers HTTPS, ALLOWED_HOSTS desde env
```
- `config/settings.py` monolítico eliminado
- `DJANGO_SETTINGS_MODULE` actualizado en `manage.py`, `wsgi.py`, `asgi.py`, `celery.py`, `docker-compose.yml`, `pytest.ini`

---

### P1-04: Validación de variables de entorno críticas al inicio

**Estado:** Pendiente  
**Problema:** `MIGO_API_TOKEN` tiene `default=''` en `base.py`. Si no se configura, las llamadas a APIMigo fallan silenciosamente en producción.

**Solución:**
```python
# config/settings/base.py
MIGO_API_TOKEN = env('MIGO_API_TOKEN')  # Sin default → ImproperlyConfigured si falta

# config/settings/local.py — agregar:
MIGO_API_TOKEN = env('MIGO_API_TOKEN', default='test_token_placeholder')
```

**Archivos afectados:** `config/settings/base.py`, `config/settings/local.py`, `.env.example`

---

## PRIORIDAD 2 — Estabilidad y Operación

> Necesarios para operar el sistema de forma confiable en producción.

### P2-01: Logging estructurado

**Estado:** Pendiente  
**Problema:** No hay configuración de logging en ningún settings. Los errores solo aparecen en consola durante desarrollo sin formato útil.

**Solución — agregar a `base.py`:**
```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'verbose'},
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
    'loggers': {
        'src.domain': {'handlers': ['console'], 'level': 'DEBUG', 'propagate': False},
        'src.infrastructure': {'handlers': ['console'], 'level': 'WARNING', 'propagate': False},
    },
}
```

**Archivos afectados:** `config/settings/base.py`

---

### P2-02: Manejo de errores en middleware de multitenancy

**Estado:** Pendiente  
**Problema:** En `middleware.py`, si `Organization.DoesNotExist` ocurre al resolver un slug de URL, el middleware falla silenciosamente. Puede causar `AttributeError` en cascada en las vistas.

**Solución:**
```python
# src/infrastructure/multitenancy/middleware.py
import logging
logger = logging.getLogger(__name__)

# dentro del método:
try:
    organization = Organization.objects.get(slug=slug)
    request.organization = organization
    set_current_organization(organization.id)
except Organization.DoesNotExist:
    logger.warning("Tenant not found for slug: %s", slug)
    return HttpResponseNotFound("Organización no encontrada")
```

**Archivos afectados:** `src/infrastructure/multitenancy/middleware.py`

---

### P2-03: Backend de email funcional en producción

**Estado:** Parcialmente resuelto — `production.py` ya tiene la configuración SMTP, pero las variables de entorno de email no están en `.env.example` con valores claros.

**Acción pendiente:** Verificar que `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` estén documentados en `.env.example` con instrucciones para SendGrid o Amazon SES.

---

### P2-04: Implementar estrategias reales de notificación

**Estado:** Pendiente  
**Problema:** `TelegramNotificationStrategy` y `WhatsAppNotificationStrategy` son stubs. Las alertas de devoluciones inusuales no llegan por estos canales.

**Solución — Telegram Bot:**
```python
# src/infrastructure/notifications/strategies.py
class TelegramNotificationStrategy(NotificationStrategy):
    def notify(self, message: str, recipient: str, **kwargs):
        token = settings.TELEGRAM_BOT_TOKEN
        httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": recipient, "text": message},
            timeout=10,
        )
```

**Archivos afectados:** `src/infrastructure/notifications/strategies.py`, `config/settings/base.py` (agregar `TELEGRAM_BOT_TOKEN`)

---

### P2-05: Pooling de conexiones a PostgreSQL

**Estado:** Pendiente  
**Problema:** Sin connection pooling, bajo carga alta el sistema puede agotar las conexiones disponibles a la DB.

**Solución inmediata (sin infra adicional):**
```python
# config/settings/base.py — dentro de DATABASES['default']:
DATABASES = {
    'default': {
        **env.db(),
        'CONN_MAX_AGE': 60,  # reutilizar conexiones por 60 segundos
    }
}
```

**Solución robusta (producción):** Agregar PgBouncer como servicio en `docker-compose.yml`.

---

### P2-06: Cobertura de pruebas ≥ 90%

**Estado:** En progreso — actual 83%  
**Áreas sin cobertura suficiente:**
- `src/interfaces/web/views.py` — dashboard, exchange rate view
- `src/infrastructure/multitenancy/middleware.py` — casos de error (slug no encontrado)
- `src/interfaces/api/views.py` — nuevos ViewSets con JWT (especialmente `TenantViewMixin` para superusers)
- `src/domain/models/users.py` — `CustomUser`, `CustomUserManager`

**Meta:** Alcanzar ≥ 90% antes de Hito 6.

---

## PRIORIDAD 3 — Calidad y Mantenibilidad

### P3-01: Paginación en todos los endpoints de lista

**Estado:** Pendiente

**Solución:**
```python
# config/settings/base.py — dentro de REST_FRAMEWORK:
REST_FRAMEWORK = {
    ...
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
}
```

---

### P3-02: Rate limiting en la API

**Estado:** Pendiente

**Solución:**
```python
# config/settings/base.py — dentro de REST_FRAMEWORK:
'DEFAULT_THROTTLE_CLASSES': [
    'rest_framework.throttling.UserRateThrottle',
],
'DEFAULT_THROTTLE_RATES': {
    'user': '500/hour',
},
```

---

### P3-03: Versionamiento de la API

**Estado:** Parcialmente cubierto — las URLs ya tienen prefijo `/api/v1/`.  
**Pendiente:** Estrategia formal de versioning en DRF para manejar cambios breaking.

---

### P3-04: CORS para clientes externos

**Estado:** Pendiente

**Solución:**
```bash
pip install django-cors-headers
```
```python
# base.py
INSTALLED_APPS = ['corsheaders', ...]
MIDDLEWARE = ['corsheaders.middleware.CorsMiddleware', ...]  # antes de CommonMiddleware
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])
```

---

### P3-05: Linting y formateo automático

**Estado:** Pendiente — agregar `ruff` + `black` al CI.

---

### P3-06: Audit trail completo para órdenes

**Estado:** Pendiente — `StockMovement` cubre inventario pero no cambios de estado en órdenes.

---

### P3-07: Type hints en servicios y modelos

**Estado:** Pendiente — cobertura actual ~15%.

---

## PRIORIDAD 4 — Evolución Arquitectónica

### P4-01: Fortalecer la capa Application (Use Cases)

**Estado:** Pendiente — la capa `application/` sigue vacía.

---

### P4-02: Objetos de Valor (Money, Quantity)

**Estado:** Pendiente

---

### P4-03: Observabilidad completa (Sentry + Prometheus)

**Estado:** Pendiente — objetivo de Hito 6.

---

### P4-04: Security scanning en CI (bandit, safety)

**Estado:** Pendiente

---

### P4-05: Resolución de tenant por subdominio

**Estado:** Pendiente — documentado en `ARCHITECTURE.md` pero no implementado.

---

## Tabla Resumen de Prioridades

| ID | Descripción | Estado | Prioridad | Esfuerzo |
|----|-------------|--------|-----------|----------|
| P1-01 | Autenticación JWT en API | ✅ Completado | 🔴 Crítica | Alto |
| P1-02 | `ALLOWED_HOSTS` restrictivo | ✅ Completado | 🔴 Crítica | Bajo |
| P1-03 | Settings por entorno | ✅ Completado | 🔴 Crítica | Medio |
| P1-04 | Validación de env vars al inicio | ⏳ Pendiente | 🔴 Crítica | Bajo |
| P2-01 | Logging estructurado | ⏳ Pendiente | 🟠 Alta | Bajo |
| P2-02 | Middleware maneja `DoesNotExist` | ⏳ Pendiente | 🟠 Alta | Bajo |
| P2-03 | Email SMTP en producción | 🔄 Parcial | 🟠 Alta | Bajo |
| P2-04 | Notificaciones Telegram/WhatsApp | ⏳ Pendiente | 🟠 Alta | Medio |
| P2-05 | Connection pooling PostgreSQL | ⏳ Pendiente | 🟠 Alta | Medio |
| P2-06 | Cobertura de pruebas ≥ 90% | 🔄 83% actual | 🟠 Alta | Medio |
| P3-01 | Paginación en endpoints | ⏳ Pendiente | 🟡 Media | Bajo |
| P3-02 | Rate limiting en API | ⏳ Pendiente | 🟡 Media | Bajo |
| P3-03 | Versionamiento de API | 🔄 Parcial | 🟡 Media | Medio |
| P3-04 | CORS para clientes externos | ⏳ Pendiente | 🟡 Media | Bajo |
| P3-05 | Linting y formateo en CI | ⏳ Pendiente | 🟡 Media | Bajo |
| P3-06 | Audit trail (django-auditlog) | ⏳ Pendiente | 🟡 Media | Medio |
| P3-07 | Type hints en servicios | ⏳ Pendiente | 🟡 Media | Alto |
| P4-01 | Capa Application con Use Cases | ⏳ Pendiente | 🔵 Largo plazo | Alto |
| P4-02 | Value Objects (Money, Quantity) | ⏳ Pendiente | 🔵 Largo plazo | Medio |
| P4-03 | Stack de observabilidad (Sentry) | ⏳ Pendiente | 🔵 Largo plazo | Alto |
| P4-04 | Security scanning en CI | ⏳ Pendiente | 🔵 Largo plazo | Bajo |
| P4-05 | Tenant por subdominio | ⏳ Pendiente | 🔵 Largo plazo | Medio |

---

## Próxima Secuencia Recomendada

```
Inmediato:   P1-04 → P2-01 → P2-02          (cierre de seguridad base)
Semana 1:    P2-05 → P2-06 → P3-01 → P3-02  (operación + calidad API)
Semana 2:    P2-04 → P3-04 → P3-05 → P3-06  (funcionalidad + CI)
Post-v1.0:   P4-01 → P4-02 → P4-03 → P4-04  (evolución arquitectónica)
```

---

## Alineación con Roadmap

| Hito | Estado | Items de este plan |
|------|--------|--------------------|
| Hito 1-4 | ✅ Completado | — |
| Hito 5 (UI/Reactividad) | 🔄 En progreso | P3-04 (CORS), P3-01 (paginación) |
| Hito 6 (Observabilidad/Cloud) | ⏳ Pendiente | P2-01, P2-03, P4-03, P4-04 |
| Post-Hito 6 | ⏳ Futuro | P4-01, P4-02, P4-05 |

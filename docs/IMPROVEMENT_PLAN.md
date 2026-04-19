# Plan de Mejoras — Nexus OMS

> **Revisión generada:** 2026-04-19  
> **Cobertura actual:** 83%  
> **Estado general:** Arquitectura sólida, requiere hardening de seguridad y preparación para producción

---

## Resumen Ejecutivo

Tras la revisión integral del proyecto se identificaron mejoras agrupadas en cuatro niveles de prioridad. Las correcciones ya aplicadas (SKU por tenant, Celery Beat/Flower, anotaciones en búsqueda de productos) resuelven los bloqueantes más urgentes. Lo que resta es principalmente seguridad, observabilidad y madurez operacional.

---

## Estado de Correcciones Aplicadas ✅

| Ítem | Estado |
|------|--------|
| `unique_together = ('organization', 'sku')` en Product | ✅ Resuelto |
| Celery Beat en `docker-compose.yml` | ✅ Resuelto |
| Flower en `docker-compose.yml` | ✅ Resuelto |
| `annotate(total_stock=Sum(...))` en búsqueda de productos | ✅ Resuelto |
| Import de `Q` en `views.py` | ✅ Resuelto |
| Cobertura de pruebas > 80% | ✅ 83% actual |

---

## PRIORIDAD 1 — Bloqueantes de Seguridad

> Deben resolverse antes de cualquier despliegue en producción o acceso externo.

### P1-01: Autenticación en la API REST

**Problema:** Los endpoints DRF son accesibles con solo el header `X-Org-ID`. Cualquier actor puede consultar datos de cualquier organización si conoce el ID.

**Impacto:** Exposición total de datos multi-tenant. Riesgo crítico de privacidad.

**Solución propuesta:**
```python
# requirements.txt
djangorestframework-simplejwt==5.x

# settings.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}
```

**Archivos afectados:** `config/settings.py`, `src/interfaces/api/views.py`, `src/interfaces/api/urls.py`

---

### P1-02: `ALLOWED_HOSTS` demasiado permisivo

**Problema:** `ALLOWED_HOSTS = ['*']` en `config/settings.py` permite cualquier host.

**Solución:**
```python
# settings.py
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])
```

**Archivos afectados:** `config/settings.py`, `.env.example`

---

### P1-03: Separar configuraciones por entorno

**Problema:** Existe un único `settings.py` para desarrollo, testing y producción. Variables críticas como `DEBUG=True` o `EMAIL_BACKEND=console` pueden filtrarse a producción.

**Solución recomendada:**
```
config/
├── settings/
│   ├── base.py        # Configuración común
│   ├── development.py # DEBUG=True, EMAIL console
│   ├── testing.py     # DB en memoria, Celery eager
│   └── production.py  # DEBUG=False, HTTPS, SMTP real
```

**Archivos afectados:** `config/settings.py` (refactor), `pytest.ini`, `docker-compose.yml`

---

### P1-04: Validación de variables de entorno críticas al inicio

**Problema:** `MIGO_API_TOKEN` tiene un valor por defecto placeholder. Si no se configura, las llamadas a APIMigo fallan silenciosamente.

**Solución:**
```python
# config/settings.py
MIGO_API_TOKEN = env('MIGO_API_TOKEN')  # Sin default → lanza ImproperlyConfigured si falta
```

**Archivos afectados:** `config/settings.py`, `.env.example`, `src/infrastructure/services/apimigo.py`

---

## PRIORIDAD 2 — Estabilidad y Operación

> Necesarios para operar el sistema de forma confiable en producción.

### P2-01: Logging estructurado

**Problema:** No hay configuración de logging en `settings.py`. Los errores solo aparecen en consola durante desarrollo.

**Solución:**
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
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/nexus.log',
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'root': {'handlers': ['console', 'file'], 'level': 'INFO'},
    'loggers': {
        'domain': {'handlers': ['console', 'file'], 'level': 'DEBUG', 'propagate': False},
    },
}
```

**Archivos afectados:** `config/settings.py`

---

### P2-02: Manejo de errores en middleware de multitenancy

**Problema:** En `middleware.py`, si `Organization.DoesNotExist` ocurre, el middleware pasa silenciosamente sin loggear ni devolver 404. Puede causar errores en cascada.

**Solución:**
```python
# infrastructure/multitenancy/middleware.py
try:
    organization = Organization.objects.get(slug=slug)
    request.organization = organization
    _thread_local.organization = organization
except Organization.DoesNotExist:
    logger.warning(f"Tenant not found for slug: {slug}")
    return HttpResponseNotFound("Organización no encontrada")
```

**Archivos afectados:** `src/infrastructure/multitenancy/middleware.py`

---

### P2-03: Backend de email funcional

**Problema:** `EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'` solo imprime emails en consola. Las notificaciones reales nunca llegan.

**Solución:**
```python
# settings/production.py
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
```

**Archivos afectados:** `config/settings.py`, `.env.example`

---

### P2-04: Implementar estrategias reales de notificación

**Problema:** Solo la estrategia de email tiene implementación básica. Telegram y WhatsApp están como stubs.

**Solución:** Implementar `TelegramNotificationStrategy` usando la API de Telegram Bot:
```python
class TelegramNotificationStrategy(NotificationStrategy):
    def notify(self, message: str, recipient: str, **kwargs):
        token = settings.TELEGRAM_BOT_TOKEN
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        httpx.post(url, json={"chat_id": recipient, "text": message})
```

**Archivos afectados:** `src/infrastructure/notifications/strategies.py`

---

### P2-05: Pooling de conexiones a PostgreSQL

**Problema:** Sin connection pooling, bajo carga alta el sistema puede agotar conexiones disponibles a la base de datos.

**Solución recomendada (PgBouncer vía Docker):**
```yaml
# docker-compose.yml
pgbouncer:
  image: edoburu/pgbouncer
  environment:
    DB_HOST: db
    DB_USER: ${POSTGRES_USER}
    DB_PASSWORD: ${POSTGRES_PASSWORD}
    POOL_MODE: transaction
    MAX_CLIENT_CONN: 100
```

**Alternativa simple:** `CONN_MAX_AGE = 60` en `DATABASES` de Django.

---

### P2-06: Cobertura de pruebas al 90%

**Estado actual:** 83%

**Áreas sin cobertura suficiente identificadas:**
- `src/interfaces/web/views.py` — Vistas de dashboard y exchange rate
- `src/infrastructure/multitenancy/middleware.py` — Casos de error
- `src/infrastructure/services/apimigo.py` — Manejo de timeouts y errores HTTP
- `src/domain/services/order_service.py` — `calculate_expected_cash` y `get_net_margin_report` con datos vacíos

**Meta:** Alcanzar ≥ 90% antes de Hito 6.

---

## PRIORIDAD 3 — Calidad y Mantenibilidad

> Mejoran la calidad del código a mediano plazo. No bloquean producción.

### P3-01: Paginación en todos los endpoints de lista

**Problema:** Los endpoints `ProductViewSet` y `OrderViewSet` no tienen paginación. Con catálogos grandes, las respuestas pueden ser enormes.

**Solución:**
```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
}
```

**Archivos afectados:** `config/settings.py`, `src/interfaces/api/views.py`

---

### P3-02: Rate limiting en la API

**Problema:** No hay límite de peticiones. La API es vulnerable a abuso o scraping.

**Solución:**
```python
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'user': '1000/day',
    },
}
```

---

### P3-03: Versionamiento de la API

**Problema:** No existe estrategia de versiones para la API REST. Un cambio breaking afectaría a todos los clientes.

**Solución recomendada:**
```python
# Rutas versionadas
urlpatterns = [
    path('api/v1/', include('src.interfaces.api.urls')),
]

# O usando DRF Namespace versioning
REST_FRAMEWORK = {
    'DEFAULT_VERSIONING_CLASS': 'rest_framework.versioning.URLPathVersioning',
}
```

---

### P3-04: CORS para clientes externos

**Problema:** No hay `django-cors-headers`. Si un cliente SPA o móvil consume la API, recibirá errores CORS.

**Solución:**
```bash
pip install django-cors-headers
```
```python
INSTALLED_APPS = ['corsheaders', ...]
MIDDLEWARE = ['corsheaders.middleware.CorsMiddleware', ...]
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])
```

---

### P3-05: Linting y formateo automático

**Problema:** No hay configuración de linters en el proyecto ni en CI.

**Solución — agregar a `pyproject.toml`:**
```toml
[tool.ruff]
line-length = 88
select = ["E", "F", "W", "I"]

[tool.black]
line-length = 88
```

**Agregar al pipeline CI (`.github/workflows/ci.yml`):**
```yaml
- name: Lint
  run: ruff check . && black --check .
```

---

### P3-06: Audit trail completo para órdenes

**Problema:** Las órdenes se cancelan mediante soft-delete pero no hay registro de quién ni cuándo realizó el cambio de estado.

**Solución recomendada:**
```bash
pip install django-auditlog
```
```python
# domain/models/sales.py
from auditlog.registry import auditlog
auditlog.register(Order, include_fields=['status', 'total_amount'])
auditlog.register(OrderReturn)
```

---

### P3-07: Type hints en servicios y modelos

**Estado actual:** ~15% del código tiene anotaciones de tipo.

**Solución gradual — comenzar por servicios:**
```python
# Antes
def create_order(organization, customer_data, items_data):

# Después
def create_order(
    organization: Organization,
    customer_data: dict[str, Any],
    items_data: list[dict[str, Any]],
) -> Order:
```

**Prioridad:** `order_service.py`, `finance.py`, `signals.py`

---

## PRIORIDAD 4 — Evolución Arquitectónica

> Mejoras de largo plazo. Aplicar cuando el sistema esté estabilizado en producción.

### P4-01: Fortalecer la capa Application

**Problema:** La capa `application/` está prácticamente vacía. Los casos de uso están directamente en Domain Services, mezclando responsabilidades.

**Solución:** Crear Use Case explícitos:
```python
# src/application/use_cases/create_order.py
class CreateOrderUseCase:
    def __init__(self, order_repo: OrderRepository, stock_repo: StockRepository):
        self.order_repo = order_repo
        self.stock_repo = stock_repo

    def execute(self, command: CreateOrderCommand) -> Order:
        ...
```

---

### P4-02: Objetos de Valor (Value Objects)

**Problema:** Conceptos como `Money`, `Quantity`, `OrderStatus` son simples strings o decimales sin validación ni comportamiento encapsulado.

**Solución:**
```python
# src/domain/value_objects.py
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "PEN"

    def __add__(self, other: "Money") -> "Money":
        assert self.currency == other.currency
        return Money(self.amount + other.amount, self.currency)
```

---

### P4-03: Observabilidad completa (Hito 6)

**Stack recomendado:**
- **Sentry** — Error tracking y performance
- **Prometheus + Grafana** — Métricas de negocio y sistema
- **Structlog** — Logging estructurado en JSON

```bash
pip install sentry-sdk[django] django-prometheus structlog
```

```python
# settings/production.py
import sentry_sdk
sentry_sdk.init(dsn=env('SENTRY_DSN'), traces_sample_rate=0.1)
```

---

### P4-04: Seguridad en CI/CD

**Agregar al pipeline:**
```yaml
- name: Security scan
  run: |
    pip install bandit safety
    bandit -r src/ -ll
    safety check
```

---

### P4-05: Resolución de tenant por subdominio

**Problema:** `ARCHITECTURE.md` documenta resolución por subdominio (`tenant.nexus.com`), pero el middleware solo implementa URL slug y header `X-Org-ID`.

**Solución — agregar al middleware:**
```python
# Extraer tenant del subdominio
host = request.get_host().split(':')[0]  # quitar puerto
parts = host.split('.')
if len(parts) >= 3:
    slug = parts[0]  # tenant.nexus.com → "tenant"
```

---

## Tabla Resumen de Prioridades

| ID | Descripción | Prioridad | Esfuerzo | Impacto |
|----|-------------|-----------|----------|---------|
| P1-01 | Autenticación JWT en API | 🔴 Crítica | Alto | Seguridad total |
| P1-02 | `ALLOWED_HOSTS` restrictivo | 🔴 Crítica | Bajo | Seguridad |
| P1-03 | Separar settings por entorno | 🔴 Crítica | Medio | Seguridad/Estabilidad |
| P1-04 | Validación de env vars al inicio | 🔴 Crítica | Bajo | Confiabilidad |
| P2-01 | Logging estructurado | 🟠 Alta | Bajo | Observabilidad |
| P2-02 | Middleware maneja `DoesNotExist` | 🟠 Alta | Bajo | Estabilidad |
| P2-03 | Email backend SMTP real | 🟠 Alta | Bajo | Funcionalidad |
| P2-04 | Notificaciones Telegram/WhatsApp | 🟠 Alta | Medio | Funcionalidad |
| P2-05 | Connection pooling PostgreSQL | 🟠 Alta | Medio | Rendimiento |
| P2-06 | Cobertura de pruebas ≥ 90% | 🟠 Alta | Medio | Calidad |
| P3-01 | Paginación en endpoints de lista | 🟡 Media | Bajo | Rendimiento |
| P3-02 | Rate limiting en API | 🟡 Media | Bajo | Seguridad |
| P3-03 | Versionamiento de API | 🟡 Media | Medio | Mantenibilidad |
| P3-04 | CORS para clientes externos | 🟡 Media | Bajo | Compatibilidad |
| P3-05 | Linting y formateo en CI | 🟡 Media | Bajo | Calidad |
| P3-06 | Audit trail (django-auditlog) | 🟡 Media | Medio | Trazabilidad |
| P3-07 | Type hints en servicios | 🟡 Media | Alto | Mantenibilidad |
| P4-01 | Capa Application con Use Cases | 🔵 Largo plazo | Alto | Arquitectura |
| P4-02 | Value Objects (Money, Quantity) | 🔵 Largo plazo | Medio | Arquitectura |
| P4-03 | Stack de observabilidad (Sentry) | 🔵 Largo plazo | Alto | Operación |
| P4-04 | Security scanning en CI | 🔵 Largo plazo | Bajo | Seguridad |
| P4-05 | Tenant por subdominio | 🔵 Largo plazo | Medio | Arquitectura |

---

## Secuencia de Implementación Recomendada

```
Semana 1-2:  P1-01 → P1-02 → P1-03 → P1-04   (seguridad base)
Semana 3-4:  P2-01 → P2-02 → P2-03 → P2-05   (operación estable)
Semana 5-6:  P2-04 → P2-06 → P3-01 → P3-02   (funcionalidad completa)
Semana 7-8:  P3-03 → P3-04 → P3-05 → P3-06   (calidad de código)
Post-v1.0:   P4-01 → P4-02 → P4-03 → P4-04   (evolución)
```

---

## Alineación con Roadmap

| Hito | Estado | Pendientes de este plan |
|------|--------|-------------------------|
| Hito 1-4 | ✅ Completado | — |
| Hito 5 (UI/Reactividad) | 🔄 En progreso | P3-04 (CORS), P3-01 (paginación) |
| Hito 6 (Observabilidad/Cloud) | ⏳ Pendiente | P1-01, P2-01, P4-03, P4-04 |
| Post-Hito 6 | ⏳ Futuro | P4-01, P4-02, P4-05 |

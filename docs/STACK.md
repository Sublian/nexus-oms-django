# Nexus Stack: The Modern Standard

### Frontend: HTMX & Tailwind CSS
* **Por qué:** Evitamos el "Over-engineering" de frameworks de JS. HTMX permite que el servidor envíe fragmentos de HTML directamente, reduciendo la latencia de desarrollo y mejorando el SEO y la simplicidad del estado.

### Async HTTP: HTTPX
* **Por qué:** `requests` es síncrono y bloquea el event loop. Usamos **HTTPX** dentro de nuestros servicios de infraestructura para interactuar con pasarelas de pago y APIs de terceros de forma asíncrona y eficiente.

### Task Queue: Celery & Redis
* **Por qué:** Redis actúa como broker de alta velocidad. Celery gestiona la resiliencia: si el servicio de correos cae, Celery reintenta la tarea con un "Exponential Backoff".

### Autenticación API: djangorestframework-simplejwt
* **Por qué:** El estándar de facto para autenticación stateless en APIs Django REST Framework. Los tokens JWT permiten que clientes externos (mobile, CLI, Postman) consuman la API sin depender de cookies de sesión. Se eligió sobre OAuth2 por la simplicidad del MVP: un token de acceso (1h) más un refresh token (7 días) cubren el ciclo completo sin servidor de autorización adicional. Los claims custom (`organization_id`, `role`) eliminan la necesidad de una consulta adicional a la base de datos en cada request.

### Settings por Entorno: django-environ + paquete de settings
* **Por qué:** Un único `settings.py` con variables de entorno mezcladas es un riesgo de seguridad y un anti-patrón. La estructura `config/settings/base|local|testing|production` fuerza separación explícita: `DEBUG`, `ALLOWED_HOSTS`, `EMAIL_BACKEND` y headers de seguridad HTTPS varían entre entornos de forma controlada y auditables en el historial de git.
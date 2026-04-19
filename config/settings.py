import environ
import os
from pathlib import Path
from celery.schedules import crontab

env = environ.Env(
    DEBUG=(bool, False)
)

BASE_DIR = Path(__file__).resolve().parent.parent

# Lee .env solo si existe (local/Docker).
# En CI las variables llegan del bloque env: del workflow.
env_file = os.path.join(BASE_DIR, '.env')
if os.path.exists(env_file):
    environ.Env.read_env(env_file)

SECRET_KEY = env('SECRET_KEY')
DEBUG = env.bool('DEBUG', default=False)

ALLOWED_HOSTS = ['*']

# ── Base de datos ──────────────────────────────────────────────────────────────
DATABASES = {
    'default': env.db(),
}

MIGO_API_TOKEN = env('MIGO_API_TOKEN', default='test_token_placeholder')

# ── Redis (única fuente de verdad para Celery y Cache) ────────────────────────
REDIS_URL = env('REDIS_URL', default='redis://redis:6379/0')

# ── Celery ────────────────────────────────────────────────────────────────────
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_ALWAYS_EAGER = env.bool('CELERY_TASK_ALWAYS_EAGER', default=False)
CELERY_BEAT_SCHEDULE = {
    'generate-weekly-reports': {
        'task': 'src.domain.tasks.generate_weekly_all_orgs',
        'schedule': crontab(minute=0, hour=0, day_of_week='monday'),
    },
    'sync-exchange-6am': {
        'task': 'tasks.sync_daily_exchange_rate',
        'schedule': crontab(hour=6, minute=0),
    },
}

# ── Cache ─────────────────────────────────────────────────────────────────────
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

# ── Apps ──────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Terceros
    'rest_framework',
    'django_htmx',
    'widget_tweaks',
    'drf_spectacular',
    'django_extensions',

    # Locales
    'src.domain',
]

# ── Middleware ────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
    'src.infrastructure.multitenancy.middleware.OrganizationMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'src' / 'templates', 
            BASE_DIR / 'src' / 'interfaces' / 'web' / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # personalizacion para inyectar la organización en el contexto global de templates
                'src.interfaces.web.context_processors.tenant_context',
                'src.interfaces.web.context_processors.exchange_rate_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ── Django REST Framework ─────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# ── drf-spectacular (Swagger) ─────────────────────────────────────────────────
SPECTACULAR_SETTINGS = {
    'TITLE': 'Nexus OMS API',
    'DESCRIPTION': 'Sistema de Gestión de Órdenes Multitenant',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'APPEND_COMPONENTS': {
        "securitySchemes": {
            "OrgIdAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-Org-ID",
                "description": "ID de la Organización para el aislamiento de datos"
            }
        }
    },
    'SECURITY': [{"OrgIdAuth": []}],
}

# ── Seguridad de contraseñas ──────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Internacionalización ──────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/Lima'
USE_I18N = True
USE_TZ = True

# ── Archivos estáticos ────────────────────────────────────────────────────────
STATIC_URL = 'static/'

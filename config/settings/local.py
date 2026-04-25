import environ

env = environ.Env()

from .base import *

DEBUG = True

ALLOWED_HOSTS = env.list(
    'ALLOWED_HOSTS',
    default=['localhost', '127.0.0.1', '0.0.0.0'],
)

# Required for ngrok and any HTTPS reverse proxy
CSRF_TRUSTED_ORIGINS = env.list(
    'CSRF_TRUSTED_ORIGINS',
    default=['http://localhost:8000', 'http://127.0.0.1:8000'],
)

# Tells Django to trust the X-Forwarded-Proto header set by ngrok/proxies
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

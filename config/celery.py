import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('nexus_oms')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Esto busca archivos tasks.py en todas las apps instaladas
app.autodiscover_tasks(['src.domain'])
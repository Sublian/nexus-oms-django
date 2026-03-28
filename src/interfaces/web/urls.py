# src/interfaces/web/urls.py

from django.urls import path
from .views import dashboard_home

app_name = 'web'

urlpatterns = [
    # Esta ruta queda vacía '' porque hereda el prefijo del include:
    # dashboard/<org_slug>/
    path('', dashboard_home, name='dashboard_home'),
]
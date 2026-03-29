# src/interfaces/web/urls.py

from django.urls import path
from .views import dashboard_home, order_detail_partial

app_name = 'web'

urlpatterns = [
    # Esta ruta queda vacía '' porque hereda el prefijo del include:
    # dashboard/<org_slug>/
    path('', dashboard_home, name='dashboard_home'),
    path('orders/<int:order_id>/', order_detail_partial, name='order_detail')
]
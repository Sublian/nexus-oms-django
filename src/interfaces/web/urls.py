# src/interfaces/web/urls.py

from django.urls import path
from .views import (
    dashboard_home, 
    order_detail_partial, 
    trigger_pdf_generation,
    organization_settings,            # La vista principal
    settings_notifications_partial,   # Pestaña 1
    settings_company_partial,          # Pestaña 2
    validate_identity_partial,
    order_create_view,
    search_client_partial,
)

app_name = 'web'

urlpatterns = [
    path('', dashboard_home, name='dashboard_home'),
    path('orders/<int:order_id>/', order_detail_partial, name='order_detail'),
    path('orders/<int:order_id>/generate-pdf/', trigger_pdf_generation, name='generate_order_pdf'),
    
    # --- Rutas de Configuración ---
    path('settings/', organization_settings, name='org-settings'),
    path('settings/notifications/', settings_notifications_partial, name='org-settings-notifications'),
    path('settings/company/', settings_company_partial, name='org-settings-company'),
    path('validate-identity/', validate_identity_partial, name='validate-identity'),
    path('orders/new/', order_create_view, name='order-create'),
    path('orders/search-client/', search_client_partial, name='search-client'),
]
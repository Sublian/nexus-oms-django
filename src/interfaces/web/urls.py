# src/interfaces/web/urls.py

from django.urls import path
from .decorators import tenant_access_required
from .views import (
    dashboard_home,
    exchange_history_view,
    order_detail_partial,
    trigger_pdf_generation,
    organization_settings,
    settings_notifications_partial,
    settings_company_partial,
    validate_identity_partial,
    order_create_view,
    search_client_partial,
    search_product_partial,
    add_product_to_order_partial,
    order_list_view,
    order_cancel_view,
    order_change_status_view,
    order_pay_modal_view,
    order_status_modal_view,
    settings_shipping_partial,
    client_list_view,
    client_detail_view,
    client_create_view,
    client_edit_view,
)

app_name = 'web'

_ta = tenant_access_required  # shorthand

urlpatterns = [
    path('', _ta(dashboard_home), name='dashboard_home'),
    path('orders/<int:order_id>/', _ta(order_detail_partial), name='order_detail'),
    path('orders/<int:order_id>/generate-pdf/', _ta(trigger_pdf_generation), name='generate_order_pdf'),

    # --- Configuración ---
    path('settings/', _ta(organization_settings), name='org-settings'),
    path('settings/notifications/', _ta(settings_notifications_partial), name='org-settings-notifications'),
    path('settings/company/', _ta(settings_company_partial), name='org-settings-company'),
    path('validate-identity/', _ta(validate_identity_partial), name='validate-identity'),

    # --- Órdenes ---
    path('orders/', _ta(order_list_view), name='order-list'),
    path('orders/search-product/', _ta(search_product_partial), name='search-product'),
    path('orders/add-item/<int:product_id>/', _ta(add_product_to_order_partial), name='add-to-order'),
    path('orders/new/', _ta(order_create_view), name='order-create'),
    path('orders/search-client/', _ta(search_client_partial), name='search-client'),
    path('orders/<int:order_id>/cancel/', _ta(order_cancel_view), name='order-cancel'),
    path('orders/<int:order_id>/status/', _ta(order_change_status_view), name='order-status'),
    path('orders/<int:order_id>/pay/', _ta(order_pay_modal_view), name='order-pay'),
    path('orders/<int:order_id>/confirm-status/', _ta(order_status_modal_view), name='order-confirm-status'),
    path('settings/shipping/', _ta(settings_shipping_partial), name='org-settings-shipping'),

    # --- Clientes ---
    path('clients/', _ta(client_list_view), name='client-list'),
    path('clients/new/', _ta(client_create_view), name='client-create'),
    path('clients/<int:client_id>/', _ta(client_detail_view), name='client-detail'),
    path('clients/<int:client_id>/edit/', _ta(client_edit_view), name='client-edit'),

    # --- Tipo de cambio ---
    path('finance/exchange-history/', _ta(exchange_history_view), name='exchange-history'),
]

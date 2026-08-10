# src/interfaces/web/urls.py

from django.urls import path
from .decorators import tenant_access_required
from .views import (
    dashboard_home,
    operational_dashboard_view,
    queue_detail_view,
    integration_logs_view,
    accounting_detail_view,
    invoice_detail_view,
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
    order_confirm_payment_view,
    order_status_modal_view,
    order_item_edit_view,
    order_item_delete_view,
    order_item_delete_confirm_view,
    settings_shipping_partial,
    client_list_view,
    client_detail_view,
    client_create_view,
    client_edit_view,
    product_list_view,
    product_detail_view,
    product_create_view,
    product_edit_view,
    product_toggle_active_view,
)

app_name = 'web'

_ta = tenant_access_required  # shorthand

urlpatterns = [
    path('', _ta(dashboard_home), name='dashboard_home'),
    path('orders/<int:order_id>/', _ta(order_detail_partial), name='order_detail'),
    path('orders/<int:order_id>/generate-pdf/', _ta(trigger_pdf_generation), name='generate_order_pdf'),

    # --- Configuración ---
    path('settings/', _ta(organization_settings), name='org_settings'),
    path('settings/notifications/', _ta(settings_notifications_partial), name='org_settings_notifications'),
    path('settings/company/', _ta(settings_company_partial), name='org_settings_company'),
    path('validate-identity/', _ta(validate_identity_partial), name='validate_identity'),

    # --- Órdenes ---
    path('orders/', _ta(order_list_view), name='order_list'),
    path('orders/search-product/', _ta(search_product_partial), name='search_product'),
    path('orders/add-item/<int:product_id>/', _ta(add_product_to_order_partial), name='add_to_order'),
    path('orders/new/', _ta(order_create_view), name='order_create'),
    path('orders/search-client/', _ta(search_client_partial), name='search_client'),
    path('orders/<int:order_id>/cancel/', _ta(order_cancel_view), name='order_cancel'),
    path('orders/<int:order_id>/status/', _ta(order_change_status_view), name='order_status'),
    path('orders/<int:order_id>/pay/', _ta(order_pay_modal_view), name='order_pay'),
    path('orders/<int:order_id>/pay/confirm/', _ta(order_confirm_payment_view), name='order_confirm_payment'),
    path('orders/<int:order_id>/confirm-status/', _ta(order_status_modal_view), name='order_confirm_status'),
    path('orders/<int:order_id>/items/<int:item_id>/edit/', _ta(order_item_edit_view), name='order_item_edit'),
    path('orders/<int:order_id>/items/<int:item_id>/delete/confirm/', _ta(order_item_delete_confirm_view), name='order_item_delete_confirm'),
    path('orders/<int:order_id>/items/<int:item_id>/delete/', _ta(order_item_delete_view), name='order_item_delete'),
    path('settings/shipping/', _ta(settings_shipping_partial), name='org_settings_shipping'),

    # --- Clientes ---
    path('clients/', _ta(client_list_view), name='client_list'),
    path('clients/new/', _ta(client_create_view), name='client_create'),
    path('clients/<int:client_id>/', _ta(client_detail_view), name='client_detail'),
    path('clients/<int:client_id>/edit/', _ta(client_edit_view), name='client_edit'),

    # --- Productos ---
    path('products/', _ta(product_list_view), name='product_list'),
    path('products/new/', _ta(product_create_view), name='product_create'),
    path('products/<int:product_id>/', _ta(product_detail_view), name='product_detail'),
    path('products/<int:product_id>/edit/', _ta(product_edit_view), name='product_edit'),
    path('products/<int:product_id>/toggle/', _ta(product_toggle_active_view), name='product_toggle'),

    # --- Tipo de cambio ---
    path('finance/exchange-history/', _ta(exchange_history_view), name='exchange_history'),

    # --- Sprint 4: Operational Dashboard ---
    path('operations/', _ta(operational_dashboard_view), name='operational_dashboard'),

    # --- FASE 2A: Drill-down views ---
    path('operations/queue/', _ta(queue_detail_view), name='operations_queue'),
    path('operations/integrations/', _ta(integration_logs_view), name='operations_integrations'),
    path('operations/accounting/', _ta(accounting_detail_view), name='operations_accounting'),

    # --- FASE 3: Invoice Observable & Timeline ---
    path('invoices/<int:order_id>/', _ta(invoice_detail_view), name='invoice_detail'),
]

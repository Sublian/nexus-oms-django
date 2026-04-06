# src\interfaces\web\views.py

from datetime import date, timedelta

from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.db.models import Sum, Count, F, ExpressionWrapper, DecimalField
from django.template.loader import render_to_string

from src.domain.models import Order, OrderItem, Organization, Payment, Product, Client
from src.domain.tasks.reporting_tasks import generate_order_pdf_task
from src.infrastructure.services.apimigo import APIMigoClient

# --- VISTAS DE CONFIGURACIÓN (TABS) ---

def organization_settings(request, org_slug):
    """Vista principal que carga el layout de configuración y la primera pestaña."""
    tenant = get_object_or_404(Organization, slug=org_slug)
    
    context = {
        'tenant': tenant,
        'active_tab': 'notifications'
    }
    return render(request, 'organizations/settings.html', context)

def settings_notifications_partial(request, org_slug):
    """Maneja la pestaña de Notificaciones (GET y POST)."""
    tenant = get_object_or_404(Organization, slug=org_slug)
    message = None

    if request.method == 'POST':
        # Actualizamos los datos del tenant
        tenant.admin_email = request.POST.get('admin_email')
        tenant.telegram_enabled = 'telegram_enabled' in request.POST
        tenant.whatsapp_enabled = 'whatsapp_enabled' in request.POST
        tenant.save()
        message = "Preferencias de notificación actualizadas."

    context = {'tenant': tenant, 'message': message}
    
    # Si es una petición HTMX, devolvemos solo el fragmento del formulario
    if request.headers.get('HX-Request'):
        return render(request, 'partials/notifications_form.html', context)
    
    # Si entran directo por URL, cargamos la página completa con esta pestaña activa
    return render(request, 'organizations/settings.html', {**context, 'active_tab': 'notifications'})

def settings_company_partial(request, org_slug):
    """Maneja la pestaña de Información de Empresa (GET y POST)."""
    tenant = get_object_or_404(Organization, slug=org_slug)
    message = None

    if request.method == 'POST':
        tenant.name = request.POST.get('name')
        tenant.ruc = request.POST.get('ruc')
        tenant.address = request.POST.get('address')
        tenant.save()
        message = "Datos fiscales actualizados correctamente."

    context = {'tenant': tenant, 'message': message}

    if request.headers.get('HX-Request'):
        return render(request, 'partials/company_form.html', context)
    
    return render(request, 'organizations/settings.html', {**context, 'active_tab': 'company'})

# Importamos el modelo si necesitas validar algo extra, 
# aunque el middleware ya debería tenerlo.
def dashboard_home(request, org_slug):
    tenant = get_object_or_404(Organization, slug=org_slug)
    batch_size = tenant.dashboard_batch_size
    
    # Obtenemos tipo de cambio (usa cache internamente si lo implementamos)
    exchange = APIMigoClient.get_exchange_rate()
    try:
        tc_value = float(exchange.get('precio_venta', 3.80))
    except (ValueError, TypeError):
        tc_value = 3.80
    
    orders = Order.objects.filter(organization=tenant).order_by('-created_at')[:batch_size]

    sales_pen = Order.objects.filter(
        organization=tenant, 
        created_at__month=date.today().month
    ).aggregate(total=Sum('total_amount'))['total'] or 0.00
    
    # --- Cálculos para las métricas ---
    now = timezone.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # 1. Ventas del Mes (Suma de total_amount de órdenes pagadas)
    monthly_sales = Order.objects.filter(
        organization=tenant,
        created_at__gte=start_of_month
    ).aggregate(total=Sum('total_amount'))['total'] or 0.00

    # 2. Stock Bajo (Productos con stock < 10, por ejemplo)
    low_stock_count = Product.objects.filter(
        organization=tenant,
        stocks__quantity__lt=10  # Puedes ajustar este umbral
    ).count()

    # 3. Margen Neto Promedio (Simulado o calculado si tienes costo_compra)
    # Aquí calculamos: (Total Ventas - Total Comisiones) / Total Ventas
    total_fees = Payment.objects.filter(
        order__organization=tenant,
        order__created_at__gte=start_of_month
    ).aggregate(fees=Sum('fee_amount'))['fees'] or 0
    
    if monthly_sales > 0:
        net_margin = ((float(monthly_sales) - float(total_fees)) / float(monthly_sales)) * 100
    else:
        net_margin = 0

    context = {
        'tenant': tenant,
        'orders': orders,
        'monthly_sales': monthly_sales,
        'monthly_sales_pen': sales_pen,
        'monthly_sales_usd': float(sales_pen) / tc_value,
        'exchange_rate': tc_value,
        'low_stock_count': low_stock_count,
        'net_margin': round(net_margin, 1),
        'batch_size': batch_size
    }
    return render(request, 'pages/dashboard_home.html', context)

def order_detail_partial(request, org_slug, order_id):
    # El middleware ya nos da el tenant
    tenant = request.organization
    
    # Buscamos el pedido asegurándonos que pertenezca a la organización (Seguridad Multi-tenant)
    order = get_object_or_404(Order, id=order_id, organization=tenant)
    items = OrderItem.objects.filter(order=order)
    
    return render(request, 'partials/order_detail_modal.html', {
        'order': order,
        'items': items
    })

def trigger_pdf_generation(request, org_slug, order_id):
    order = get_object_or_404(Order, id=order_id, organization__slug=org_slug)
    generate_order_pdf_task.delay(order.id)
    
    # Respuesta con estética de "botón en proceso"
    return HttpResponse(f'''
        <div hx-get="/dashboard/{org_slug}/orders/{order_id}/" 
             hx-trigger="load delay:3s" 
             hx-target="#order-modal" 
             hx-select="#order-modal"
             class="w-full py-4 bg-gray-900 text-tenant-secondary rounded-xl font-black flex items-center justify-center gap-3 uppercase text-xs tracking-[0.1em] animate-pulse">
            
            <svg class="animate-spin h-4 w-4 text-tenant-secondary" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            
            <span>Sincronizando Archivo...</span>
        </div>
        <p class="text-[9px] text-center text-gray-400 mt-2 font-bold tracking-tighter uppercase opacity-60">
            La tarea se ha delegado al worker de reporting
        </p>
    ''')


def validate_identity_partial(request, org_slug):
    document = request.GET.get('document', '').strip()
    length = len(document)
    
    # Log interno para debug
    print(f"DEBUG: Validating {document} for tenant {org_slug}")

    if length == 8:
        data = APIMigoClient.get_dni(document)
        if data:
            if data.get('success'):
                nombre = data.get('nombre')
                return HttpResponse(f'<span class="text-green-600 text-xs font-bold">✓ {nombre}</span>'
                                    f'<script>document.getElementsByName("name")[0].value = "{nombre}";</script>')
            else:
                return HttpResponse('<span class="text-red-500 text-xs">Error en data de DNI</span>')
        return HttpResponse('<span class="text-amber-500 text-xs">DNI no encontrado en RENIEC (Migo)</span>')

    elif length == 11:
        data = APIMigoClient.get_ruc(document)
        if data:
            if data.get('success'):
                nombre = data.get('nombre_o_razon_social')
                direccion = data.get('direccion_simple') or data.get('direccion', '')
                return HttpResponse(f'<span class="text-green-600 text-xs font-bold">✓ {nombre}</span>'
                                    f'<script>'
                                    f'document.getElementsByName("name")[0].value = "{nombre}";'
                                    f'document.getElementsByName("address")[0].value = "{direccion}";'
                                    f'</script>')
        return HttpResponse('<span class="text-amber-500 text-xs">RUC no encontrado en SUNAT</span>')

    return HttpResponse('<span class="text-gray-400 text-xs">Documento incompleto...</span>')


def order_create_view(request, org_slug):
    tenant = get_object_or_404(Organization, slug=org_slug)
    
    # Obtenemos el objeto (ahora garantizado por el refactor anterior)
    exchange = APIMigoClient.get_exchange_rate()
    
    # Extraemos el valor de venta con un fallback final
    # Usamos float() para asegurar que sea operable en el template o JS
    try:
        tc_value = float(exchange.get('precio_venta', 3.80))
    except (ValueError, TypeError):
        tc_value = 3.80

    context = {
        'tenant': tenant,
        'exchange_rate': tc_value,
        'currency_base': 'PEN',
        'is_api_online': exchange.get('success', False)
    }
    return render(request, 'orders/order_form.html', context)

def search_client_partial(request, org_slug):
    query = request.GET.get('document', '').strip()
    tenant = get_object_or_404(Organization, slug=org_slug)
    
    # 1. Buscar en DB local
    client = Client.objects.filter(organization=tenant, document_number=query).first()
    
    if client:
        return render(request, 'orders/partials/client_selected.html', {'client': client})
    
    # 2. Si no existe y tiene longitud de DNI/RUC, sugerir validación externa
    if len(query) in [8, 11]:
        return HttpResponse(f"""
            <div class="p-3 bg-blue-50 border border-blue-200 rounded-lg flex justify-between items-center">
                <span class="text-sm text-blue-700">Cliente no registrado localmente.</span>
                <button type="button" 
                        hx-get="/{org_slug}/validate-identity/?document={query}" 
                        hx-target="#client-result"
                        class="text-xs bg-blue-600 text-white px-3 py-1 rounded shadow">
                    Consultar a Migo.pe
                </button>
            </div>
        """)
    
    return HttpResponse('<span class="text-gray-400 text-xs">Ingrese un documento válido...</span>')


def search_product_partial(request, org_slug):
    query = request.GET.get('q', '').strip()
    tenant = get_object_or_404(Organization, slug=org_slug)
    
    if len(query) < 3:
        return HttpResponse("") # No buscar hasta tener 3 letras

    # Buscamos por nombre o SKU (si tienes ese campo)
    products = Product.objects.filter(
        organization=tenant, 
        name__icontains=query,
        stock__gt=0 # Solo productos con stock
    )[:5] # Limitar a 5 resultados para el dropdown
    
    # return render(request, 'orders/partials/product_results.html', {
    return render(request, 'orders/product_results.html', {
        'products': products,
        'tenant': tenant
    })


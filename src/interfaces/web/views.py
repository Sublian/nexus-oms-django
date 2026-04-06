# src\interfaces\web\views.py

from datetime import date, timedelta

from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Count, F, ExpressionWrapper, DecimalField
from django.template.loader import render_to_string
from django.core.paginator import Paginator

from src.domain.models import Order, OrderItem, Organization, Payment, Product, Client, Stock
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


@transaction.atomic
def order_create_view(request, org_slug):
    tenant = get_object_or_404(Organization, slug=org_slug)
    
    if request.method == 'POST':
        try:
            # 1. Obtener datos del form
            doc_number = request.POST.get('document')
            client_name = request.POST.get('name')
            product_ids = request.POST.getlist('product_ids[]')
            quantities = request.POST.getlist('quantities[]')

            # 2. Obtener/Crear Cliente
            # Nota: document_type lo pondremos como DNI/RUC según el largo o un default
            doc_type = 'RUC' if len(doc_number) == 11 else 'DNI'
            client, _ = Client.objects.get_or_create(
                organization=tenant,
                document_number=doc_number,
                defaults={
                    'name': client_name,
                    'document_type': doc_type
                }
            )

            # 3. Crear la Orden (Usando los nombres exactos de tu modelo)
            order = Order.objects.create(
                organization=tenant,
                client=client, # Solo si agregaste la FK, si no, quita esta línea
                customer_name=client.name,
                customer_email=client.email or "sin@correo.com",
                status='DRAFT',
                subtotal=0,
                tax_amount=0,
                total_amount=0
            )

            total_subtotal = 0
            
            # 4. Procesar Items
            for p_id, qty in zip(product_ids, quantities):
                qty = int(qty)
                if qty <= 0: continue
                
                product = Product.objects.select_for_update().get(id=p_id, organization=tenant)
                
                # Descuento de stock simple (puedes mejorar la lógica de bodega luego)
                stock_record = Stock.objects.filter(product=product, quantity__gte=qty).first()
                if not stock_record:
                    raise ValueError(f"No hay stock suficiente para: {product.name}")
                
                stock_record.quantity -= qty
                stock_record.save()

                # Cálculo de montos del item
                price = float(product.price)
                item_subtotal = price * qty
                
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=qty,
                    price_at_order=price,
                    organization=tenant
                )
                total_subtotal += item_subtotal

            # 5. Cálculos Finales (IGV 18%)
            # Si el precio ya incluye IGV:
            order.total_amount = total_subtotal
            order.subtotal = float(total_subtotal) / 1.18
            order.tax_amount = float(total_subtotal) - order.subtotal
            order.save()

            messages.success(request, f"Pedido #{order.id} creado correctamente.")
            
            if request.headers.get('HX-Request'):
                res = HttpResponse(status=204)
                res['HX-Redirect'] = f"/dashboard/{org_slug}/orders/" # O a la lista de pedidos
                return res
            
            return redirect('web:order-list', org_slug=org_slug)

        except Exception as e:
            messages.error(request, f"Error al procesar el pedido: {str(e)}")
            # El rollback es automático por el @transaction.atomic
            # transaction.rollback()

    # --- Lógica GET (ya la tenías, asegúrate de mantenerla) ---
    exchange = APIMigoClient.get_exchange_rate()
    tc_value = float(exchange.get('precio_venta', 3.80))
    
    context = {
        'tenant': tenant,
        'exchange_rate': tc_value,
        'currency_base': 'PEN',
        'api_status': 'online' if exchange.get('success') else 'offline'
    }
    return render(request, 'orders/order_form.html', context)


def search_client_partial(request, org_slug):
    tenant = get_object_or_404(Organization, slug=org_slug)
    doc_number = request.GET.get('document', '').strip()

    if len(doc_number) < 8: # Evitar búsquedas vacías o incompletas
        return HttpResponse("")
    
    # 1. Buscar en DB local
    client = Client.objects.filter(organization=tenant, document_number=doc_number).first()
    
    if client:
        # return render(request, 'orders/client_selected.html', {'client': client})
        return render(request, 'orders/partials/client_selected.html', {
            'client': client,
            'source': 'local'
        })
    
    # 2. Si no existe y tiene longitud de DNI/RUC, sugerir validación externa
    if len(doc_number) in [8, 11]:
        validate_url = f"/dashboard/{org_slug}/validate-identity/?document={doc_number}"
        return HttpResponse(f"""
            <div class="p-2 bg-blue-50 border border-blue-100 rounded-lg flex flex-col gap-2">
                <span class="text-[10px] text-blue-600 font-bold uppercase">No registrado localmente</span>
                <button type="button" 
                        hx-get="{validate_url}" 
                        hx-target="#client-result"
                        class="bg-blue-600 text-white text-xs py-1 px-2 rounded hover:bg-blue-700 transition-colors">
                    🔍 Consultar Migo.pe
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
    # Anotamos el stock_total sumando las cantidades en todas las bodegas (Warehouse)
    products = Product.objects.filter(
        organization=tenant,
        is_active=True,
        name__icontains=query
    ).annotate(
        total_stock=Sum('stocks__quantity')
    ).filter(
        total_stock__gt=0  # Solo productos que realmente tengan algo en alguna bodega
    )[:5]
    
    return render(request, 'orders/product_results.html', {
        'products': products,
        'tenant': tenant
    })


def add_product_to_order_partial(request, org_slug, product_id):
    tenant = get_object_or_404(Organization, slug=org_slug)
    
    # Obtenemos el producto anotando el stock total disponible
    product = get_object_or_404(
        Product.objects.filter(organization=tenant).annotate(
            total_available=Sum('stocks__quantity')
        ), 
        id=product_id
    )
    
    # Aseguramos un valor numérico para el stock (evitar None)
    stock_max = product.total_available or 0
    
    # Renderizamos la fila usando el valor anotado
    return HttpResponse(f'''
        <tr class="border-b border-gray-100 animate-in fade-in duration-300">
            <td class="px-4 py-3">
                <input type="hidden" name="product_ids[]" value="{product.id}">
                <span class="text-sm font-medium text-gray-800">{product.name}</span>
            </td>
            <td class="px-4 py-3">
                <input type="number" name="quantities[]" value="1" min="1" max="{stock_max}"
                       class="w-16 border-gray-300 rounded text-sm p-1 focus:ring-tenant-primary quantity-input"
                       onchange="updateRowSubtotal(this, {product.price:.2f})">
            </td>
            <td class="px-4 py-3 text-sm font-mono text-gray-600">
                S/ {product.price:.2f}
            </td>
            <td class="px-4 py-3 text-sm font-bold text-gray-950 row-subtotal">
                S/ {product.price:.2f}
            </td>
            <td class="px-4 py-3 text-right">
                <button type="button" onclick="removeRow(this)" class="text-red-400 hover:text-red-600">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                    </svg>
                </button>
            </td>
        </tr>
    ''')

def order_list_view(request, org_slug):
    tenant = get_object_or_404(Organization, slug=org_slug)
    
    # Filtros básicos
    query = request.GET.get('q')
    status = request.GET.get('status')
    
    orders = Order.objects.filter(organization=tenant).select_related('client') # Si tienes el manager
    
    if not hasattr(orders, 'order_with_total_amount'): # Fallback si no hay manager optimizado
        orders = Order.objects.filter(organization=tenant).select_related('client').order_by('-created_at')

    if query:
        orders = orders.filter(customer_name__icontains=query) | orders.filter(id__icontains=query)
    
    if status:
        orders = orders.filter(status=status)

    paginator = Paginator(orders, 15) # 15 pedidos por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'orders/order_list.html', {
        'tenant': tenant,
        'orders': page_obj,
        'status_choices': Order.STATUS_CHOICES
    })
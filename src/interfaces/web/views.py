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
from django.views.decorators.http import require_POST
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q, Sum

from decimal import Decimal

from src.domain.models import Order, OrderItem, Organization, Payment, Product, Client, Stock, StockMovement, Category, Warehouse
from src.domain.models.finance import ExchangeRate
from src.domain.services.finance_service import ExchangeService
from src.domain.tasks.reporting_tasks import generate_order_pdf_task
from src.infrastructure.services.apimigo import APIMigoClient


def _modal_success(request, order, tenant):
    """
    Closes the modal (main swap on #modals-here) and updates the order row in-place (OOB).

    Why the table wrapper:
    DOMParser promotes bare <tr> into an implicit <table><tbody> structure, so HTMX's
    outerHTML swap would replace the row with a full nested table.  Wrapping the row in
    <table><tbody> keeps the <tr> as a proper DOM node; hx-swap-oob="outerHTML:#id" then
    locates the existing row by CSS selector and replaces only that element.
    """
    row_html = render_to_string(
        'orders/partials/order_row.html',
        {'order': order, 'tenant': tenant},
        request=request,
    )
    row_oob = row_html.replace(
        f'<tr id="order-row-{order.id}"',
        f'<tr id="order-row-{order.id}" hx-swap-oob="outerHTML:#order-row-{order.id}"',
        1,
    )
    return HttpResponse(
        f'<div id="modals-here"></div>'
        f'<table><tbody>{row_oob}</tbody></table>'
    )

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
    exchange_obj = ExchangeService.get_current_rate()
    tc_value = float(exchange_obj.sell_price)
        
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

            if not product_ids:
                raise ValueError("Debes agregar al menos un producto al pedido.")

            delivery_type = request.POST.get('delivery_type', 'PICKUP')
            delivery_address = request.POST.get('delivery_address', '').strip()
            shipping_fee = tenant.default_shipping_fee if delivery_type == 'DELIVERY' else Decimal('0.00')

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
                client=client,
                customer_name=client.name,
                customer_email=client.email or "sin@correo.com",
                status='DRAFT',
                delivery_type=delivery_type,
                delivery_address=delivery_address if delivery_type == 'DELIVERY' else '',
                shipping_fee=shipping_fee,
                subtotal=0,
                tax_amount=0,
                total_amount=0,
            )

            total_subtotal = Decimal('0')

            # 4. Procesar Items
            for p_id, qty in zip(product_ids, quantities):
                qty = int(qty)
                if qty <= 0: continue

                product = Product.objects.select_for_update().get(id=p_id, organization=tenant)

                stock_record = Stock.objects.filter(product=product, quantity__gte=qty).first()
                if not stock_record:
                    raise ValueError(f"No hay stock suficiente para: {product.name}")

                price = product.price  # already Decimal
                item_subtotal = price * qty

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=qty,
                    price_at_order=price,
                    organization=tenant
                )
                total_subtotal += item_subtotal

            # 5. Cálculos Finales (precio incluye IGV 18%)
            order.subtotal = (total_subtotal / Decimal('1.18')).quantize(Decimal('0.01'))
            order.tax_amount = (total_subtotal - order.subtotal).quantize(Decimal('0.01'))
            order.total_amount = total_subtotal + shipping_fee
            order.save()

            messages.success(request, f"Pedido #{order.id} creado correctamente.")
            
            if request.headers.get('HX-Request'):
                res = HttpResponse(status=204)
                res['HX-Redirect'] = f"/dashboard/{org_slug}/orders/" # O a la lista de pedidos
                return res
            
            return redirect('web:order-list', org_slug=org_slug)

        except ValueError as e:
            messages.error(request, f"Error de validación: {str(e)}")
        except DjangoValidationError as e:
            messages.error(request, f"Error en datos: {e.message}")
        except Exception as e:
            messages.error(request, f"Error al procesar el pedido: {str(e)}")
            # El rollback es automático por el @transaction.atomic
            # transaction.rollback()

    # --- Lógica GET (ya la tenías, asegúrate de mantenerla) ---
    # exchange = APIMigoClient.get_exchange_rate()
    exchange_obj = ExchangeService.get_current_rate()
    tc_value = float(exchange_obj.sell_price)
    
    context = {
        'tenant': tenant,
        'exchange_rate': tc_value,
        'currency_base': 'PEN',
        'api_status': 'online' if exchange_obj.origin != 'fallback' else 'offline'
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
    
    # Base del queryset optimizada
    products_qs = Product.objects.filter(
        organization=tenant,
        is_active=True
    ).annotate(
        total_stock=Sum('stocks__quantity')
    ).filter(
        total_stock__gt=0
    )

    if query:
        # Filtrado por nombre o SKU
        products = products_qs.filter(
            Q(name__icontains=query) | Q(sku__icontains=query)
        ).order_by('name')[:8]
    else:
        # Al hacer clic sin escribir, mostramos los primeros 5 alfabéticamente
        # O podrías usar .order_by('-id') si quieres ver los últimos creados
        products = products_qs.order_by('name')[:5]
    
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



@require_POST
def order_cancel_view(request, org_slug, order_id):
    tenant = get_object_or_404(Organization, slug=org_slug)
    order = get_object_or_404(Order, id=order_id, organization=tenant)

    if 'CANCELLED' in Order.VALID_TRANSITIONS.get(order.status, []):
        _restore_order_stock(order)
        order.status = 'CANCELLED'
        order.save()

    return render(request, 'orders/partials/order_row.html', {'order': order, 'tenant': tenant})


def order_pay_modal_view(request, org_slug, order_id):
    tenant = get_object_or_404(Organization, slug=org_slug)
    order = get_object_or_404(Order, id=order_id, organization=tenant)

    if 'PAID' not in Order.VALID_TRANSITIONS.get(order.status, []):
        return HttpResponse('Transición no permitida', status=400)

    if request.method == 'POST':
        # Sanity check: verify stock hasn't gone negative
        for item in order.items.select_related('product'):
            stock = Stock.objects.filter(product=item.product, organization=tenant).first()
            if not stock or stock.quantity < 0:
                return HttpResponse(
                    f'Stock insuficiente para {item.product.name}. Contacta a administración.',
                    status=400
                )

        method = request.POST.get('method', '').strip()
        reference = request.POST.get('reference', '').strip() or None
        fee = (order.total_amount * Decimal('0.035')).quantize(Decimal('0.01')) if method == 'CARD' else Decimal('0.00')

        Payment.objects.get_or_create(
            order=order,
            defaults={
                'organization': tenant,
                'method': method,
                'amount': order.total_amount,
                'transaction_reference': reference,
                'fee_amount': fee,
                'payment_date': timezone.now(),
            },
        )
        order.status = 'PAID'
        order.save()
        return _modal_success(request, order, tenant)

    return render(request, 'orders/partials/pay_modal.html', {
        'order': order,
        'tenant': tenant,
        'payment_methods': Payment.PaymentMethod.choices,
    })


def order_status_modal_view(request, org_slug, order_id):
    tenant = get_object_or_404(Organization, slug=org_slug)
    order = get_object_or_404(Order, id=order_id, organization=tenant)

    if request.method == 'POST':
        new_status = request.POST.get('status', '').strip()
        valid_next = Order.VALID_TRANSITIONS.get(order.status, [])
        if new_status not in valid_next:
            return HttpResponse('Transición no válida', status=400)
        if new_status == 'CANCELLED':
            _restore_order_stock(order)
        order.status = new_status
        order.save()
        return _modal_success(request, order, tenant)

    new_status = request.GET.get('to', '')
    return render(request, 'orders/partials/status_confirm_modal.html', {
        'order': order,
        'tenant': tenant,
        'new_status': new_status,
        'new_status_display': dict(Order.STATUS_CHOICES).get(new_status, new_status),
    })


def settings_shipping_partial(request, org_slug):
    tenant = get_object_or_404(Organization, slug=org_slug)
    message = None
    if request.method == 'POST':
        try:
            tenant.default_shipping_fee = Decimal(request.POST.get('default_shipping_fee', '10'))
            tenant.save()
            message = 'Tarifa de envío actualizada.'
        except Exception:
            message = 'Valor no válido.'

    context = {'tenant': tenant, 'message': message}
    if request.headers.get('HX-Request'):
        return render(request, 'organizations/partials/shipping_form.html', context)
    return render(request, 'organizations/settings.html', {**context, 'active_tab': 'shipping'})


def client_list_view(request, org_slug):
    from src.infrastructure.multitenancy.thread_local import set_current_organization
    tenant = get_object_or_404(Organization, slug=org_slug)
    set_current_organization(tenant.id)

    query = request.GET.get('q', '').strip()

    clients = (
        Client.objects.filter(organization=tenant)
        .annotate(order_count=Count('orders'))
        .order_by('name')
    )

    if query:
        clients = clients.filter(
            Q(name__icontains=query) |
            Q(document_number__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query)
        )

    total_count = clients.count()
    paginator = Paginator(clients, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'clients/client_list.html', {
        'tenant': tenant,
        'page_obj': page_obj,
        'query': query,
        'total_count': total_count,
    })


def client_detail_view(request, org_slug, client_id):
    from src.infrastructure.multitenancy.thread_local import set_current_organization
    tenant = get_object_or_404(Organization, slug=org_slug)
    set_current_organization(tenant.id)
    client = get_object_or_404(Client, id=client_id, organization=tenant)

    orders = (
        Order.objects.filter(organization=tenant, client=client)
        .annotate(
            items_count=Count('items'),
            total_qty=Sum('items__quantity'),
        )
        .order_by('-created_at')
    )

    stats = orders.aggregate(
        total_orders=Count('id'),
        total_spent=Sum('total_amount'),
    )

    return render(request, 'clients/client_detail.html', {
        'tenant': tenant,
        'client': client,
        'orders': orders,
        'stats': stats,
    })


def _client_form_context(tenant, error, post_data, client=None, is_edit=False, org_slug=''):
    from django.urls import reverse
    doc_types = Client.DOCUMENT_TYPES
    if is_edit:
        cancel_url = reverse('web:client-detail', kwargs={'org_slug': org_slug, 'client_id': client.id})
        current = {
            'document_type': post_data.get('document_type', client.document_type),
            'document_number': post_data.get('document_number', client.document_number),
            'name': post_data.get('name', client.name),
            'email': post_data.get('email', client.email or ''),
            'phone': post_data.get('phone', client.phone or ''),
            'address': post_data.get('address', client.address or ''),
        }
    else:
        cancel_url = reverse('web:client-list', kwargs={'org_slug': org_slug})
        current = {k: post_data.get(k, '') for k in ['document_type', 'document_number', 'name', 'email', 'phone', 'address']}
        if not current['document_type']:
            current['document_type'] = 'DNI'

    return {
        'tenant': tenant,
        'client': client,
        'error': error,
        'current': current,
        'doc_types': doc_types,
        'cancel_url': cancel_url,
        'form_title': f'Editar — {client.name}' if is_edit else 'Nuevo Cliente',
        'submit_label': 'Guardar Cambios' if is_edit else 'Crear Cliente',
    }


def client_create_view(request, org_slug):
    from src.infrastructure.multitenancy.thread_local import set_current_organization
    tenant = get_object_or_404(Organization, slug=org_slug)
    set_current_organization(tenant.id)

    error = None
    post_data = request.POST if request.method == 'POST' else {}

    if request.method == 'POST':
        doc_type = post_data.get('document_type', '').strip()
        doc_number = post_data.get('document_number', '').strip()
        name = post_data.get('name', '').strip()

        if not doc_type or not doc_number or not name:
            error = 'Tipo de documento, número y nombre son obligatorios.'
        elif Client.objects.filter(organization=tenant, document_number=doc_number).exists():
            error = f'Ya existe un cliente con el documento {doc_number}.'
        else:
            Client.objects.create(
                organization=tenant,
                document_type=doc_type,
                document_number=doc_number,
                name=name.upper(),
                email=post_data.get('email', '').strip() or None,
                phone=post_data.get('phone', '').strip() or None,
                address=post_data.get('address', '').strip() or None,
            )
            messages.success(request, f'Cliente {name.upper()} creado correctamente.')
            return redirect('web:client-list', org_slug=org_slug)

    ctx = _client_form_context(tenant, error, post_data, is_edit=False, org_slug=org_slug)
    return render(request, 'clients/client_form.html', ctx)


def client_edit_view(request, org_slug, client_id):
    from src.infrastructure.multitenancy.thread_local import set_current_organization
    tenant = get_object_or_404(Organization, slug=org_slug)
    set_current_organization(tenant.id)
    client = get_object_or_404(Client, id=client_id, organization=tenant)

    error = None
    post_data = request.POST if request.method == 'POST' else {}

    if request.method == 'POST':
        doc_type = post_data.get('document_type', '').strip()
        doc_number = post_data.get('document_number', '').strip()
        name = post_data.get('name', '').strip()

        if not doc_type or not doc_number or not name:
            error = 'Tipo de documento, número y nombre son obligatorios.'
        elif (
            Client.objects.filter(organization=tenant, document_number=doc_number)
            .exclude(id=client_id)
            .exists()
        ):
            error = f'Ya existe otro cliente con el documento {doc_number}.'
        else:
            client.document_type = doc_type
            client.document_number = doc_number
            client.name = name.upper()
            client.email = post_data.get('email', '').strip() or None
            client.phone = post_data.get('phone', '').strip() or None
            client.address = post_data.get('address', '').strip() or None
            client.save()
            messages.success(request, f'Cliente {client.name} actualizado correctamente.')
            return redirect('web:client-detail', org_slug=org_slug, client_id=client_id)

    ctx = _client_form_context(tenant, error, post_data, client=client, is_edit=True, org_slug=org_slug)
    return render(request, 'clients/client_form.html', ctx)


def _product_form_context(tenant, error, post_data, product=None, is_edit=False, org_slug=''):
    from django.urls import reverse
    categories = Category.objects.filter(organization=tenant).order_by('name')
    warehouses = Warehouse.objects.filter(organization=tenant).order_by('name')

    if is_edit and product:
        cancel_url = reverse('web:product-detail', kwargs={'org_slug': org_slug, 'product_id': product.id})
        current = {
            'name': post_data.get('name', product.name),
            'sku': post_data.get('sku', product.sku),
            'description': post_data.get('description', product.description),
            'price': post_data.get('price', str(product.price)),
            'category_name': post_data.get('category_name', product.category.name if product.category else ''),
            'is_active': product.is_active,
        }
    else:
        cancel_url = reverse('web:product-list', kwargs={'org_slug': org_slug})
        current = {
            'name': post_data.get('name', ''),
            'sku': post_data.get('sku', ''),
            'description': post_data.get('description', ''),
            'price': post_data.get('price', ''),
            'category_name': post_data.get('category_name', ''),
            'is_active': True,
        }

    return {
        'tenant': tenant,
        'org_slug': org_slug,
        'product': product,
        'error': error,
        'current': current,
        'categories': categories,
        'warehouses': warehouses,
        'is_edit': is_edit,
        'cancel_url': cancel_url,
    }


def product_list_view(request, org_slug):
    from src.infrastructure.multitenancy.thread_local import set_current_organization
    tenant = get_object_or_404(Organization, slug=org_slug)
    set_current_organization(tenant.id)

    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', 'active')
    category_id = request.GET.get('category', '')

    qs = (
        Product.objects.filter(organization=tenant)
        .select_related('category')
        .annotate(stock_total=Sum('stocks__quantity'))
        .order_by('name')
    )

    if query:
        qs = qs.filter(Q(name__icontains=query) | Q(sku__icontains=query) | Q(description__icontains=query))

    if status_filter == 'active':
        qs = qs.filter(is_active=True)
    elif status_filter == 'inactive':
        qs = qs.filter(is_active=False)

    if category_id:
        qs = qs.filter(category_id=category_id)

    categories = Category.objects.filter(organization=tenant).order_by('name')
    total_count = qs.count()

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'products/product_list.html', {
        'tenant': tenant,
        'org_slug': org_slug,
        'page_obj': page_obj,
        'total_count': total_count,
        'query': query,
        'status_filter': status_filter,
        'categories': categories,
        'category_id': category_id,
    })


def product_detail_view(request, org_slug, product_id):
    from src.infrastructure.multitenancy.thread_local import set_current_organization
    tenant = get_object_or_404(Organization, slug=org_slug)
    set_current_organization(tenant.id)
    product = get_object_or_404(Product, id=product_id, organization=tenant)

    stocks = Stock.objects.filter(product=product).select_related('warehouse').order_by('warehouse__name')
    stock_total = stocks.aggregate(total=Sum('quantity'))['total'] or 0

    orders = (
        Order.objects.filter(items__product=product, organization=tenant)
        .distinct()
        .annotate(
            product_qty=Sum('items__quantity', filter=Q(items__product=product)),
            product_subtotal=Sum(
                ExpressionWrapper(
                    F('items__quantity') * F('items__price_at_order'),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                ),
                filter=Q(items__product=product),
            ),
        )
        .order_by('-created_at')
    )

    return render(request, 'products/product_detail.html', {
        'tenant': tenant,
        'org_slug': org_slug,
        'product': product,
        'stocks': stocks,
        'stock_total': stock_total,
        'orders': orders,
    })


def product_create_view(request, org_slug):
    from src.infrastructure.multitenancy.thread_local import set_current_organization
    tenant = get_object_or_404(Organization, slug=org_slug)
    set_current_organization(tenant.id)

    error = None
    post_data = request.POST if request.method == 'POST' else {}

    if request.method == 'POST':
        name = post_data.get('name', '').strip()
        sku = post_data.get('sku', '').strip().upper()
        price_raw = post_data.get('price', '').strip()
        description = post_data.get('description', '').strip()
        category_name = post_data.get('category_name', '').strip()
        warehouse_id = post_data.get('warehouse_id', '').strip()
        initial_qty_raw = post_data.get('initial_qty', '').strip()

        if not name or not sku or not price_raw:
            error = 'Nombre, SKU y precio son obligatorios.'
        else:
            try:
                price = Decimal(price_raw)
                if price <= 0:
                    raise ValueError
            except Exception:
                error = 'El precio debe ser un número positivo.'

        if not error and Product.objects.filter(organization=tenant, sku=sku).exists():
            error = f'Ya existe un producto con el SKU {sku}.'

        if not error:
            category = None
            if category_name:
                category = Category.objects.filter(organization=tenant, name__iexact=category_name).first()
                if not category:
                    category = Category.objects.create(organization=tenant, name=category_name)

            product = Product.objects.create(
                organization=tenant,
                name=name,
                sku=sku,
                price=price,
                description=description,
                category=category,
                is_active=True,
            )

            if warehouse_id and initial_qty_raw:
                try:
                    initial_qty = int(initial_qty_raw)
                    warehouse = Warehouse.objects.get(id=warehouse_id, organization=tenant)
                    Stock.objects.create(
                        organization=tenant,
                        product=product,
                        warehouse=warehouse,
                        quantity=max(0, initial_qty),
                    )
                except Exception:
                    pass

            messages.success(request, f'Producto {product.name} creado correctamente.')
            return redirect('web:product-detail', org_slug=org_slug, product_id=product.id)

    ctx = _product_form_context(tenant, error, post_data, is_edit=False, org_slug=org_slug)
    return render(request, 'products/product_form.html', ctx)


def product_edit_view(request, org_slug, product_id):
    from src.infrastructure.multitenancy.thread_local import set_current_organization
    tenant = get_object_or_404(Organization, slug=org_slug)
    set_current_organization(tenant.id)
    product = get_object_or_404(Product, id=product_id, organization=tenant)

    error = None
    post_data = request.POST if request.method == 'POST' else {}

    if request.method == 'POST':
        name = post_data.get('name', '').strip()
        sku = post_data.get('sku', '').strip().upper()
        price_raw = post_data.get('price', '').strip()
        description = post_data.get('description', '').strip()
        category_name = post_data.get('category_name', '').strip()

        if not name or not sku or not price_raw:
            error = 'Nombre, SKU y precio son obligatorios.'
        else:
            try:
                price = Decimal(price_raw)
                if price <= 0:
                    raise ValueError
            except Exception:
                error = 'El precio debe ser un número positivo.'

        if not error and Product.objects.filter(organization=tenant, sku=sku).exclude(id=product_id).exists():
            error = f'Ya existe otro producto con el SKU {sku}.'

        if not error:
            category = None
            if category_name:
                category = Category.objects.filter(organization=tenant, name__iexact=category_name).first()
                if not category:
                    category = Category.objects.create(organization=tenant, name=category_name)

            product.name = name
            product.sku = sku
            product.price = price
            product.description = description
            product.category = category
            product.save()

            messages.success(request, f'Producto {product.name} actualizado correctamente.')
            return redirect('web:product-detail', org_slug=org_slug, product_id=product.id)

    ctx = _product_form_context(tenant, error, post_data, product=product, is_edit=True, org_slug=org_slug)
    return render(request, 'products/product_form.html', ctx)


@require_POST
def product_toggle_active_view(request, org_slug, product_id):
    from src.infrastructure.multitenancy.thread_local import set_current_organization
    tenant = get_object_or_404(Organization, slug=org_slug)
    set_current_organization(tenant.id)
    product = get_object_or_404(Product, id=product_id, organization=tenant)

    product.is_active = not product.is_active
    product.save()

    label = 'activado' if product.is_active else 'suspendido'
    messages.success(request, f'Producto {product.name} {label} correctamente.')
    return redirect('web:product-detail', org_slug=org_slug, product_id=product.id)


def _restore_order_stock(order):
    """Restores stock for all items on a cancelled order."""
    for item in order.items.select_related('product'):
        stock = Stock.objects.filter(
            product=item.product,
            organization=order.organization
        ).first()
        if stock:
            stock.quantity += item.quantity
            stock.save()


def _recalculate_order_totals(order):
    """Recalculates subtotal/tax/total from current items (prices include 18% IGV)."""
    items = list(order.items.all())
    total_with_tax = sum(item.price_at_order * item.quantity for item in items)
    order.subtotal = (total_with_tax / Decimal('1.18')).quantize(Decimal('0.01'))
    order.tax_amount = (total_with_tax - order.subtotal).quantize(Decimal('0.01'))
    order.total_amount = (total_with_tax + order.shipping_fee).quantize(Decimal('0.01'))
    order.save()


@require_POST
def order_change_status_view(request, org_slug, order_id):
    tenant = get_object_or_404(Organization, slug=org_slug)
    order = get_object_or_404(Order, id=order_id, organization=tenant)
    new_status = request.POST.get('status', '').strip()

    valid_next = Order.VALID_TRANSITIONS.get(order.status, [])
    if new_status not in valid_next:
        return HttpResponse(status=400)

    if new_status == 'CANCELLED':
        _restore_order_stock(order)

    order.status = new_status
    order.save()
    return render(request, 'orders/partials/order_row.html', {'order': order, 'tenant': tenant})


@transaction.atomic
def order_item_edit_view(request, org_slug, order_id, item_id):
    tenant = get_object_or_404(Organization, slug=org_slug)
    order = get_object_or_404(Order, id=order_id, organization=tenant)
    item = get_object_or_404(OrderItem, id=item_id, order=order)

    if order.status not in ('DRAFT', 'PENDING'):
        return HttpResponse('Edición no permitida en este estado', status=400)

    if request.method == 'POST':
        error = None
        try:
            new_qty = int(request.POST.get('quantity', 0))
            if new_qty <= 0:
                raise ValueError('La cantidad debe ser mayor a 0')

            diff = new_qty - item.quantity
            if diff > 0:
                stock = Stock.objects.select_for_update().filter(
                    product=item.product,
                    organization=tenant,
                    quantity__gte=diff,
                ).first()
                if not stock:
                    raise ValueError(f'Stock insuficiente para {item.product.name}')
                stock.quantity -= diff
                stock.save()
                StockMovement.objects.create(
                    organization=tenant,
                    stock=stock,
                    quantity=diff,
                    movement_type=StockMovement.MovementType.OUTPUT,
                    reason=f'Ajuste cantidad: Pedido #{order.id}',
                    order=order,
                )
            elif diff < 0:
                stock = Stock.objects.filter(product=item.product, organization=tenant).first()
                if stock:
                    stock.quantity += abs(diff)
                    stock.save()
                    StockMovement.objects.create(
                        organization=tenant,
                        stock=stock,
                        quantity=abs(diff),
                        movement_type=StockMovement.MovementType.RETURN,
                        reason=f'Ajuste cantidad: Pedido #{order.id}',
                        order=order,
                    )

            item.quantity = new_qty
            item.save()
            _recalculate_order_totals(order)
        except (ValueError, TypeError) as e:
            error = str(e)
            return render(request, 'orders/partials/item_edit_form.html', {
                'order': order, 'item': item, 'org_slug': org_slug, 'error': error,
            })

        items = order.items.select_related('product').all()
        return render(request, 'partials/order_detail_modal.html', {'order': order, 'items': items})

    # GET — render inline edit form
    return render(request, 'orders/partials/item_edit_form.html', {
        'order': order,
        'item': item,
        'org_slug': org_slug,
    })


@require_POST
@transaction.atomic
def order_item_delete_view(request, org_slug, order_id, item_id):
    tenant = get_object_or_404(Organization, slug=org_slug)
    order = get_object_or_404(Order, id=order_id, organization=tenant)
    item = get_object_or_404(OrderItem, id=item_id, order=order)

    if order.status not in ('DRAFT', 'PENDING'):
        return HttpResponse('Eliminación no permitida en este estado', status=400)

    stock = Stock.objects.filter(product=item.product, organization=tenant).first()
    if stock:
        stock.quantity += item.quantity
        stock.save()
        StockMovement.objects.create(
            organization=tenant,
            stock=stock,
            quantity=item.quantity,
            movement_type=StockMovement.MovementType.RETURN,
            reason=f'Eliminación de ítem: Pedido #{order.id}',
            order=order,
        )

    item.delete()
    _recalculate_order_totals(order)

    items = order.items.select_related('product').all()
    return render(request, 'partials/order_detail_modal.html', {'order': order, 'items': items})


## tipo de cambio

def exchange_history_view(request, org_slug):
    # Mantenemos el tenant para el contexto de la UI (sidebar, navbar, etc.)
    tenant = get_object_or_404(Organization, slug=org_slug)
    
    # Eliminamos el filtro de organization que causaba el FieldError
    rates = ExchangeRate.objects.all().order_by('-date', '-created_at')

    paginator = Paginator(rates, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'finance/exchange_history.html', {
        'tenant': tenant,
        'rates': page_obj,
    })
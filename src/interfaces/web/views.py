from django.shortcuts import render,get_object_or_404
from src.domain.models import Order, OrderItem
# Importamos el modelo si necesitas validar algo extra, 
# aunque el middleware ya debería tenerlo.

def dashboard_home(request, org_slug):
    # El middleware ya validó la organización en request.organization
    tenant = request.organization
    
    # Traemos los últimos 5 pedidos de esta organización
    recent_orders = Order.objects.filter(
        organization=tenant
    ).order_by('-created_at')[:5]
    print(f"Tenant: {tenant} | pedidos_recientes: {recent_orders}")
    return render(request, 'pages/dashboard_home.html', {
        'orders': recent_orders
    })

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
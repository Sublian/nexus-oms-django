from django.shortcuts import render
from src.domain.models import Order
# Importamos el modelo si necesitas validar algo extra, 
# aunque el middleware ya debería tenerlo.

def dashboard_home(request, org_slug):
    # El middleware ya validó la organización en request.organization
    tenant = request.organization
    
    # Traemos los últimos 5 pedidos de esta organización
    recent_orders = Order.objects.filter(
        organization=tenant
    ).order_by('-created_at')[:5]
    
    return render(request, 'pages/dashboard_home.html', {
        'orders': recent_orders
    })
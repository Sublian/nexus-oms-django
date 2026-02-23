from celery import shared_task
import time
from django.db.models import Sum, Count

from .models import Order, SalesReport, Organization

@shared_task
def process_order_notifications(order_id):
    """
    Tarea asíncrona para procesar notificaciones post-venta.
    """
    print(f"📧 Iniciando proceso de notificación para el Pedido #{order_id}...")
    
    # Simulamos un proceso pesado (ej: conectar con un servidor de correos)
    time.sleep(5) 
    
    print(f"✅ Notificación enviada exitosamente para el Pedido #{order_id}")
    return True

@shared_task
def generate_sales_report_task(organization_id):
    org = Organization.objects.get(id=organization_id)
    
    # El filtrado es automático si usamos el manager de la organización 
    # o manual si estamos en un proceso de fondo sin middleware
    orders = Order.objects.filter(organization=org)
    
    stats = orders.aggregate(
        total_revenue=Sum('total_amount'),
        count=Count('id')
    )

    report_data = {
        'revenue': float(stats['total_revenue'] or 0),
        'total_orders': stats['count'],
        'status_breakdown': list(orders.values('status').annotate(total=Count('status')))
    }

    report = SalesReport.objects.create(
        organization=org,
        total_sales=report_data['revenue'],
        order_count=report_data['total_orders'],
        data=report_data
    )
    
    return f"Reporte #{report.id} generado para {org.name}"

@shared_task
def generate_weekly_all_orgs():
    for org in Organization.objects.all():
        generate_sales_report_task.delay(org.id)
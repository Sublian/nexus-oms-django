from celery import shared_task
import time
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count, F

from .models import Order, OrderReturn, SalesReport, Organization

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
def generate_sales_report_task(organization_id, start_date=None, end_date=None):
    org = Organization.objects.get(id=organization_id)

    # Manejo de fechas por defecto (Hoy)
    if not end_date:
        end_date = timezone.now()
    if not start_date:
        start_date = end_date.replace(hour=0, minute=0, second=0, microsecond=0)

    orders = Order.objects.filter(
        organization=org,
        created_at__range=(start_date, end_date)
    )
    returns = OrderReturn.objects.filter(
        organization=org,
        created_at__range=(start_date, end_date)
    )

    # 1. Cálculo de Ingresos Brutos
    stats = orders.aggregate(
        gross_revenue=Sum('total_amount'),
        order_count=Count('id')
    )

    # 2. Cálculo de Pérdidas por Devoluciones
    # Multiplicamos la cantidad devuelta por el precio actual del producto
    # (En una fase avanzada, usaríamos el precio histórico del OrderItem)
    total_returned_value = returns.aggregate(
        total=Sum(F('quantity') * F('product__price'))
    )['total'] or 0

    gross_revenue = float(stats['gross_revenue'] or 0)
    net_revenue = gross_revenue - float(total_returned_value)

    report_data = {
        'gross_revenue': gross_revenue,
        'net_revenue': net_revenue,
        'total_returned_value': float(total_returned_value),
        'total_orders': stats['order_count'],
        'total_returns': returns.count(),
        'status_breakdown': list(orders.values('status').annotate(total=Count('status'))),
        'return_reasons': list(returns.values('reason').annotate(count=Count('reason')))
    }

    # Guardamos el reporte con el valor NETO
    report = SalesReport.objects.create(
        organization=org,
        total_sales=net_revenue,
        order_count=stats['order_count'],
        # Guardamos el rango en el JSON para auditoría
        data={
            **report_data,
            'period_start': start_date.isoformat(),
            'period_end': end_date.isoformat(),
        }
    )
    
    return f"Reporte de Salud Financiera #{report.id} generado para {org.name}"

@shared_task
def trigger_periodic_reports(frequency='daily'):
    end_date = timezone.now()
    
    if frequency == 'weekly':
        start_date = end_date - timedelta(days=7)
    elif frequency == 'monthly':
        start_date = end_date - timedelta(days=30)
    else: # daily
        start_date = end_date - timedelta(days=1)

    for org in Organization.objects.all():
        generate_sales_report_task.delay(org.id, start_date, end_date)

@shared_task
def generate_weekly_all_orgs():
    for org in Organization.objects.all():
        generate_sales_report_task.delay(org.id)

@shared_task
def alert_unusual_return_task(return_id):
    ret = OrderReturn.objects.get(id=return_id)
    # Aquí simularíamos un envío de correo al gerente
    print(f"⚠️ ALERTA DE BODEGA: Devolución inusual registrada (ID: {return_id}). Motivo: OTHERS. Notas: {ret.notes}")
    return True


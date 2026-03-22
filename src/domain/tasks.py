from celery import shared_task
import time
from datetime import datetime
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count, F

from src.domain.notifications.service import NotificationService

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

def calculate_growth(current, previous):
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 2)

@shared_task
def generate_sales_report_task(organization_id, start_date=None, end_date=None):
    org = Organization.objects.get(id=organization_id)

    # Manejo de fechas por defecto (Hoy)
    if not end_date: end_date = timezone.now()
    if not start_date: start_date = end_date - timedelta(days=1)

    # 2. Definir Periodo Anterior (para comparación)
    duration = end_date - start_date
    prev_start = start_date - duration
    prev_end = start_date

    # 3. Obtener métricas de ambos periodos
    def get_metrics(start, end):
        orders = Order.objects.filter(organization=org, created_at__range=(start, end))
        returns = OrderReturn.objects.filter(organization=org, created_at__range=(start, end))
        
        gross = orders.aggregate(total=Sum('total_amount'))['total'] or 0
        ret_val = returns.aggregate(total=Sum(F('quantity') * F('product__price')))['total'] or 0
        
        return {
            'revenue': float(gross) - float(ret_val),
            'count': orders.count()
        }

    current_stats = get_metrics(start_date, end_date)
    previous_stats = get_metrics(prev_start, prev_end)

    # 4. Calcular Crecimiento (%)
    growth_pct = calculate_growth(current_stats['revenue'], previous_stats['revenue'])

    report_data = {
        'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()},
        'metrics': current_stats,
        'comparison': {
            'previous_revenue': previous_stats['revenue'],
            'growth_percentage': growth_pct,
            'status': 'UP' if growth_pct >= 0 else 'DOWN'
        }
    }

    report = SalesReport.objects.create(
        organization=org,
        total_sales=current_stats['revenue'],
        order_count=current_stats['count'],
        data=report_data
    )

    NotificationService.notify_report_ready(
        organization_config={
            'telegram_enabled': org.telegram_enabled,
            'whatsapp_enabled': org.whatsapp_enabled
        },
        user_email=org.admin_email,
        report_name="Ventas Mensuales"
    )
    
    return f"Reporte #{report.id} generado. Crecimiento: {growth_pct}%"

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
def generate_monthly_report_task(organization_id, month=None, year=None):
    # 1. Definir el rango del mes
    now = timezone.now()
    month = month or now.month
    year = year or now.year
    
    # Crear llave única para Redis: e.g., "report_nike_03_2026"
    org = Organization.objects.get(id=organization_id)
    cache_key = f"report_{org.name.lower()}_{month:02d}_{year}"
    
    # Intentar obtener de caché primero
    cached_data = cache.get(cache_key)
    if cached_data:
        return f"Reporte obtenido de CACHÉ para {org.name}"

    # 2. Definir fechas inicio y fin de mes
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)

    # 3. Cálculos (Usa la lógica de Ingreso Neto que definimos antes)
    orders = Order.objects.filter(organization=org, created_at__range=(start_date, end_date))
    returns = OrderReturn.objects.filter(organization=org, created_at__range=(start_date, end_date))
    
    def get_metrics(start, end):
        orders = Order.objects.filter(organization=org, created_at__range=(start, end))
        returns = OrderReturn.objects.filter(organization=org, created_at__range=(start, end))
        
        gross = orders.aggregate(total=Sum('total_amount'))['total'] or 0
        ret_val = returns.aggregate(total=Sum(F('quantity') * F('product__price')))['total'] or 0
        
        return {
            'revenue': float(gross) - float(ret_val),
            'count': orders.count()
        }
    
    current_stats = get_metrics(start_date, end_date)
    
    report_data = {
        "month": month,
        "year": year,
        "revenue": current_stats['revenue'],
        "total_orders": current_stats['count'],
        "generated_at": timezone.now().isoformat()
    }

    # 4. Guardar en DB y en CACHÉ (por 24 horas)
    SalesReport.objects.create(
        organization=org,
        total_sales=current_stats['revenue'],
        order_count=current_stats['count'],
        data=report_data
    )
    
    cache.set(cache_key, report_data, timeout=86400) # 86400 segundos = 1 día
    
    return f"Reporte MENSUAL generado y cacheado para {org.name} ({month}/{year})"        

@shared_task
def alert_unusual_return_task(return_id):
    ret = OrderReturn.objects.get(id=return_id)
    # Aquí simularíamos un envío de correo al gerente
    print(f"⚠️ ALERTA DE BODEGA: Devolución inusual registrada (ID: {return_id}). Motivo: OTHERS. Notas: {ret.notes}")
    return True


import time
from datetime import datetime, timedelta
from weasyprint import HTML
from celery import shared_task

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, F
from django.template.loader import render_to_string
from django.core.files.base import ContentFile

from src.domain.notifications.service import NotificationService

from ..models import Order, SalesReport, Organization

def calculate_growth(current, previous):
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 2)

def _get_org_metrics(org, start, end):
    """
    Ahora delegamos la responsabilidad al servicio financiero.
    """
    # Usamos la función que moviste a services.py
    from ..services import get_net_margin_report
    financial_data = get_net_margin_report(org, start, end)
    
    # Contamos las órdenes para mantener la compatibilidad con el reporte actual
    order_count = Order.objects.filter(organization=org, created_at__range=(start, end)).count()
    
    return {
        'revenue': float(financial_data['revenue']),
        'net_profit': float(financial_data['net_profit']),
        'cogs': float(financial_data['cogs']),
        'fees': float(financial_data['fees']),
        'margin_pct': float(financial_data['margin_percentage']),
        'count': order_count
    }

# --- TASKS ---

@shared_task
def generate_sales_report_task(organization_id, start_date=None, end_date=None):
    try:
        org = Organization.objects.get(id=organization_id)
        
        if not end_date: end_date = timezone.now()
        if not start_date: start_date = end_date - timedelta(days=1)

        duration = end_date - start_date
        current_stats = _get_org_metrics(org, start_date, end_date)
        previous_stats = _get_org_metrics(org, start_date - duration, start_date)

        growth_pct = calculate_growth(current_stats['revenue'], previous_stats['revenue'])

        # Ahora el JSONField (data) será mucho más rico en información
        report_data = {
            'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()},
            'metrics': current_stats, # Aquí ya viajan net_profit, cogs, etc.
            'comparison': {
                'previous_revenue': previous_stats['revenue'],
                'growth_percentage': growth_pct,
                'status': 'UP' if growth_pct >= 0 else 'DOWN'
            }
        }

        with transaction.atomic():
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
            report_name=f"Reporte de Ventas ({start_date.strftime('%d/%m')})"
        )
        return f"Reporte #{report.id} para {org.name} generado con éxito."

    except Organization.DoesNotExist:
        return f"Error: Organización {organization_id} no encontrada."
    except Exception as e:
        # Aquí podrías loguear el error con sentry o similar
        return f"Fallo en generación de reporte: {str(e)}"

@shared_task
def generate_monthly_report_task(organization_id, month=None, year=None):
    now = timezone.now()
    month = month or now.month
    year = year or now.year
    
    org = Organization.objects.get(id=organization_id)
    cache_key = f"report_{org.slug}_{month:02d}_{year}" # Usar slug es más seguro que name.lower()
    
    cached_data = cache.get(cache_key)
    if cached_data:
        return f"Reporte obtenido de CACHÉ para {org.name}"

    # FIX: Hacer las fechas 'Aware' (con zona horaria)
    start_date = timezone.make_aware(datetime(year, month, 1))
    if month == 12:
        end_date = timezone.make_aware(datetime(year + 1, 1, 1))
    else:
        end_date = timezone.make_aware(datetime(year, month + 1, 1))

    current_stats = _get_org_metrics(org, start_date, end_date)
    
    report_data = {
        "month": month, "year": year,
        "revenue": current_stats['revenue'],
        "total_orders": current_stats['count'],
        "generated_at": timezone.now().isoformat()
    }

    with transaction.atomic():
        SalesReport.objects.create(
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
        report_name=f"Cierre Mensual - {month}/{year}"
    )
    
    cache.set(cache_key, report_data, timeout=86400)
    return f"Reporte MENSUAL generado para {org.name}"

@shared_task
def trigger_periodic_reports(frequency='daily'):
    """
    Orquestador que utiliza .iterator() para eficiencia de memoria.
    """
    end_date = timezone.now()
    days = {'weekly': 7, 'monthly': 30, 'daily': 1}.get(frequency, 1)
    start_date = end_date - timedelta(days=days)

    # .iterator() es mejor práctica para grandes volúmenes de datos
    for org in Organization.objects.all().iterator():
        generate_sales_report_task.delay(org.id, start_date, end_date)

@shared_task
def generate_weekly_all_orgs():
    """Restaurada: Dispara reportes para todas las orgs cada semana"""
    for org in Organization.objects.all().iterator():
        generate_sales_report_task.delay(org.id)

@shared_task(bind=True, max_retries=3)
def generate_order_pdf_task(self, order_id):
    try:
        order = Order.objects.get(id=order_id)
        
        # 1. Renderizar el HTML con el estilo Tailwind (usando CDN para el PDF)
        html_string = render_to_string('dashboard/reports/order_print.html', {
            'order': order,
            'items': order.items.all(),
        })

        # 2. Generar el PDF
        pdf_file = HTML(string=html_string).write_pdf()

        # 3. Guardar el PDF en el modelo o en un storage
        # Supongamos que añadimos un campo 'pdf_report' a Order
        filename = f"order_{order.id}_{order.organization.slug}.pdf"
        order.pdf_report.save(filename, ContentFile(pdf_file))
        order.save()

        return f"PDF generado exitosamente para la orden {order_id}"
        
    except Exception as exc:
        # Reintento en caso de fallo (ej. DB ocupada)
        raise self.retry(exc=exc, countdown=10)


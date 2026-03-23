from celery import shared_task
from django.core.cache import cache
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, F
from datetime import datetime, timedelta
import time

from src.domain.notifications.service import NotificationService

from ..models import  OrderReturn

@shared_task
def process_order_notifications(order_id):
    # Simulamos proceso pesado
    time.sleep(2) # Reducido para no eternizar los tests
    return f"Notificación procesada para Pedido #{order_id}"

@shared_task
def alert_unusual_return_task(return_id):
    """
    Restaurada: Ahora usa el NotificationService para alertar a los gerentes.
    """
    try:
        ret = OrderReturn.objects.get(id=return_id)
        org = ret.organization
        
        # En lugar de solo un print, usamos nuestro servicio multi-canal
        NotificationService.notify_report_ready(
            organization_config={
                'telegram_enabled': org.telegram_enabled,
                'whatsapp_enabled': org.whatsapp_enabled
            },
            user_email=org.admin_email,
            report_name=f"⚠️ ALERTA: Devolución Inusual ID {return_id}"
        )
        return f"Alerta enviada para devolución {return_id}"
    except Exception as e:
        return f"Error en alerta de devolución: {str(e)}"
    
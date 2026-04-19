# src\domain\tasks\finance_tasks.py

import logging
from celery import shared_task

from src.domain.services.finance_service import ExchangeService

logger = logging.getLogger(__name__)

@shared_task(name="tasks.sync_daily_exchange_rate")
def sync_daily_exchange_rate():
    """Tarea programada para refrescar el tipo de cambio cada mañana."""
    logger.info("Iniciando sincronización diaria de tipo de cambio...")
    rate = ExchangeService.get_current_rate()
    if rate:
        logger.info(f"Tipo de cambio sincronizado: Compra {rate.buy_price} - Venta {rate.sell_price}")
    else:
        logger.error("No se pudo sincronizar el tipo de cambio.")
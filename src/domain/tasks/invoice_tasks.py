import logging

from celery import shared_task
from django.db import transaction

logger = logging.getLogger("invoice_task")


@shared_task(
    bind=True,
    name="tasks.create_invoice",
    max_retries=5,
    autoretry_for=(),       # control manual — decidimos qué se reintenta
    retry_backoff=True,
    retry_backoff_max=600,  # max 10 min entre retries
)
def create_invoice_task(self, order_id: int):
    from src.domain.models import Order
    from src.application.usecases.create_invoice import CreateInvoiceUseCase
    from src.domain.exceptions import NubefactTemporaryError, NubefactPermanentError

    task_id = self.request.id
    logger.info(f"[InvoiceTask][task_id={task_id}][order_id={order_id}][action=START]")

    # Fase 1: lock corto — idempotencia + marcar processing
    # No ejecutar nada externo dentro del lock (evita bloquear DB)
    with transaction.atomic():
        try:
            order = Order.objects.select_for_update().get(id=order_id)
        except Order.DoesNotExist:
            logger.error(f"[InvoiceTask][order_id={order_id}][action=ORDER_NOT_FOUND]")
            return

        if order.invoice_external_id:
            logger.info(
                f"[InvoiceTask][task_id={task_id}][order_id={order_id}][action=SKIP_ALREADY_ISSUED]"
            )
            return

        if order.invoice_status == 'processing':
            logger.warning(
                f"[InvoiceTask][task_id={task_id}][order_id={order_id}][action=SKIP_ALREADY_PROCESSING]"
            )
            return

        order.invoice_status = 'processing'
        order.invoice_attempts += 1
        order.save(update_fields=['invoice_status', 'invoice_attempts'])

    # Fase 2: ejecutar fuera del lock
    try:
        usecase = CreateInvoiceUseCase()
        result = usecase.execute(order)

        if result.get('status') == 'issued':
            Order.objects.filter(id=order_id).update(invoice_last_error=None)

        logger.info(
            f"[InvoiceTask][task_id={task_id}][order_id={order_id}]"
            f"[action=COMPLETED][status={result.get('status')}]"
        )
        return result

    except NubefactTemporaryError as exc:
        # Timeout, 502, 503 — retry con backoff exponencial
        logger.warning(
            f"[InvoiceTask][task_id={task_id}][order_id={order_id}]"
            f"[action=RETRY][error={str(exc)}][attempt={self.request.retries + 1}]"
        )
        Order.objects.filter(id=order_id).update(
            invoice_status='retrying',
            invoice_last_error=str(exc)[:500],
        )
        raise self.retry(exc=exc)

    except NubefactPermanentError as exc:
        # 400, auth error — no reintentar
        logger.error(
            f"[InvoiceTask][task_id={task_id}][order_id={order_id}]"
            f"[action=FAILED_PERMANENT][error={str(exc)}]"
        )
        Order.objects.filter(id=order_id).update(
            invoice_status='failed',
            invoice_last_error=str(exc)[:500],
        )
        return

    except Exception as exc:
        logger.exception(
            f"[InvoiceTask][task_id={task_id}][order_id={order_id}][action=FAILED_UNKNOWN]"
        )
        Order.objects.filter(id=order_id).update(
            invoice_status='failed',
            invoice_last_error=str(exc)[:500],
        )
        raise

"""
Sync de pagos pendientes de confirmación (transferencias / Yape-Plin).

Flujo:
  sync_pending_payments_task  (Beat, cada 60s)
    └── sync_single_payment_task.delay(payment_id)  x N

Garantias:
  - Idempotencia: solo se procesan payments con status='pending'
  - Lock DB (select_for_update): evita confirmación doble entre workers
  - Toda la lógica de negocio vive en PaymentService — el task solo orquesta
"""
import logging

from celery import shared_task
from django.db import transaction

logger = logging.getLogger("payment_sync")


@shared_task(bind=True, name="tasks.sync_pending_payments")
def sync_pending_payments_task(self):
    """
    Barre todos los pagos pendientes (todos los tenants) y despacha una task
    por cada uno. Usa all_objects para operar sobre TODOS los tenants.
    """
    from src.domain.models import Payment

    payment_ids = list(
        Payment.all_objects
        .filter(status=Payment.Status.PENDING)
        .values_list('id', flat=True)
    )

    for payment_id in payment_ids:
        sync_single_payment_task.delay(payment_id)

    logger.info(
        f"[payment.sync.sweep][task_id={self.request.id}][dispatched={len(payment_ids)}]"
    )
    return len(payment_ids)


@shared_task(bind=True, name="tasks.sync_single_payment", max_retries=0)
def sync_single_payment_task(self, payment_id: int):
    """
    Consulta el estado de un pago pendiente en la pasarela y, si aprueba,
    marca la orden PAID + workflow.
    """
    from src.domain.models import Payment
    from src.application.services.payment_service import PaymentService

    task_id = self.request.id or "eager"

    # Phase 1: lock + idempotencia (atomic corto)
    try:
        with transaction.atomic():
            try:
                payment = (
                    Payment.all_objects
                    .select_for_update()
                    .select_related('order')
                    .get(id=payment_id)
                )
            except Payment.DoesNotExist:
                logger.warning(
                    f"[payment.sync.not_found][task_id={task_id}][payment_id={payment_id}]"
                )
                return

            if payment.status != Payment.Status.PENDING:
                logger.info(
                    f"[payment.sync.skip][task_id={task_id}]"
                    f"[payment_id={payment_id}][reason=not_pending][status={payment.status}]"
                )
                return

            order_id = payment.order_id
            org_id = payment.organization_id
    except Exception as exc:
        logger.error(
            f"[payment.sync.lock_failed][task_id={task_id}][payment_id={payment_id}][error={exc}]"
        )
        raise

    logger.info(
        f"[payment.sync.started][task_id={task_id}]"
        f"[tenant_id={org_id}][order_id={order_id}][payment_id={payment_id}]"
    )

    # Phase 2: confirmación (fuera del lock)
    try:
        payment, result = PaymentService(logger).confirm_payment(payment)
        logger.info(
            f"[payment.sync.done][task_id={task_id}]"
            f"[tenant_id={org_id}][order_id={order_id}]"
            f"[payment_id={payment_id}][status={payment.status}]"
        )
        return payment.status
    except Exception as exc:
        logger.exception(
            f"[payment.sync.error][task_id={task_id}]"
            f"[tenant_id={org_id}][order_id={order_id}]"
            f"[payment_id={payment_id}][error={exc}]"
        )
        raise

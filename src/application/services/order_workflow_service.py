from django.db import transaction

from src.domain.models.order_constants import OrderStatus
from src.domain.models import OrderWorkflowLog


class OrderWorkflowService:

    def __init__(self, logger):
        self.logger = logger

    def handle_order_paid(self, order):
        # Guardia: solo procesar ordenes en estado PAID
        if order.status != OrderStatus.PAID:
            self.logger.warning(
                f"[OrderWorkflow][order_id={order.id}][action=VALIDATION_FAIL][reason=status_not_paid]"
            )
            return

        # Fast-path: objeto en memoria ya procesado (llamadas secuenciales)
        if order.workflow_processed:
            self.logger.warning(
                f"[OrderWorkflow][order_id={order.id}][action=SKIP_ALREADY_PROCESSED]"
            )
            return

        # DB lock: re-fetch con select_for_update para prevenir race condition
        # _claim_workflow_lock es patcheable en unit tests (sin DB).
        if not self._claim_workflow_lock(order):
            self.logger.warning(
                f"[OrderWorkflow][order_id={order.id}][action=SKIP_ALREADY_PROCESSED]"
            )
            return

        # order.workflow_status ya es 'processing' (seteado por _claim_workflow_lock)
        self.logger.info(f"[OrderWorkflow][order_id={order.id}][action=START]")
        self._audit_log(order, 'start', order.workflow_status)

        try:
            self._log_order_paid(order)
            self._trigger_invoicing(order)

            order.workflow_processed = True
            order.workflow_status = 'completed'
            self.logger.info(f"[OrderWorkflow][order_id={order.id}][action=END]")
            self._audit_log(order, 'completed', order.workflow_status)

        except Exception as e:
            order.workflow_status = 'failed'
            self.logger.error(
                f"[OrderWorkflow][order_id={order.id}][action=ERROR][error={str(e)}]"
            )
            self._audit_log(order, 'error', 'failed', metadata={'error': str(e)})
            raise

    def _claim_workflow_lock(self, order):
        # Re-fetch con lock de DB para prevenir procesamiento doble concurrente.
        # Retorna True si el lock fue reclamado, False si ya estaba procesado.
        from src.domain.models import Order

        with transaction.atomic():
            locked = Order.objects.select_for_update().get(id=order.id)
            if locked.workflow_processed:
                return False
            locked.workflow_status = 'processing'
            locked.save(update_fields=['workflow_status'])

        # Sincronizar objeto en memoria para que el save() de la view sea consistente
        order.workflow_status = 'processing'
        return True

    def _log_order_paid(self, order):
        self.logger.info(f"[OrderWorkflow][order_id={order.id}][action=ACTION_EXECUTED][step=payment_confirmed]")
        self._audit_log(order, 'action_executed', order.workflow_status)

    def _trigger_invoicing(self, order):
        from src.domain.tasks.invoice_tasks import create_invoice_task
        self.logger.info(f"[OrderWorkflow][order_id={order.id}][action=INVOICING_TRIGGERED][status=async]")
        self._audit_log(order, 'invoicing_triggered', order.workflow_status)
        create_invoice_task.delay(order.id)

    def _audit_log(self, order, action, status, metadata=None):
        try:
            OrderWorkflowLog.objects.create(
                organization=order.organization,
                order=order,
                action=action,
                status=status,
                metadata=metadata or {}
            )
        except Exception as e:
            self.logger.warning(
                f"[OrderWorkflow][order_id={order.id}][action=AUDIT_LOG_FAILED][error={str(e)}]"
            )

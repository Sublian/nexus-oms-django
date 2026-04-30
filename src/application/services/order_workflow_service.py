# Único punto de orquestación para el flujo post-pago de una orden.
# No usar signals ni lógica en modelos — toda la magia va aquí.
# Fase 2: Resiliencia, Async (Celery), Retry logic, Auditoría
from src.domain.models.order_constants import OrderStatus
from src.domain.models import OrderWorkflowLog
from ..usecases.create_invoice import CreateInvoiceUseCase


# Nota: CreateInvoiceUseCase es inyectable para testing.
# En Fase 2, Nubefact se conecta en el UseCase, no aquí en el workflow.


class OrderWorkflowService:

    def __init__(self, logger, create_invoice_usecase=None):
        self.logger = logger
        self.create_invoice_usecase = create_invoice_usecase

    def handle_order_paid(self, order):
        # 1. Guardia: solo procesar órdenes en estado PAID
        if order.status != OrderStatus.PAID:
            self.logger.warning(
                f"[OrderWorkflow][order_id={order.id}][action=VALIDATION_FAIL][reason=status_not_paid]"
            )
            return

        # 2. Idempotencia: persistente en DB — idempotencia real, no simulada
        if order.workflow_processed:
            self.logger.warning(
                f"[OrderWorkflow][order_id={order.id}][action=SKIP_ALREADY_PROCESSED]"
            )
            return

        self.logger.info(f"[OrderWorkflow][order_id={order.id}][action=START]")
        self._audit_log(order, 'start', order.workflow_status)

        # 3. Marcar como procesando ANTES de ejecutar
        # Si pasa algo, al menos sabemos que se intentó
        order.workflow_status = 'processing'

        try:
            # 4. Pasos del flujo — execution-safe, failure-aware
            self._log_order_paid(order)
            self._trigger_invoicing(order)

            # 5. Solo marcar completado si TODO salió bien
            order.workflow_processed = True
            order.workflow_status = 'completed'
            self.logger.info(f"[OrderWorkflow][order_id={order.id}][action=END]")
            self._audit_log(order, 'completed', order.workflow_status)

        except Exception as e:
            # 6. Capturar fallos sin romper el workflow
            # Marcar estado como fallido para retry/manual intervention
            order.workflow_status = 'failed'
            self.logger.error(
                f"[OrderWorkflow][order_id={order.id}][action=ERROR][error={str(e)}]"
            )
            self._audit_log(order, 'error', 'failed', metadata={'error': str(e)})
            # Re-raise para que caller sepa que algo falló
            raise

    def _log_order_paid(self, order):
        # Fase 1: solo logging. Fase 2: aquí irá llamada a Nubefact.
        self.logger.info(f"[OrderWorkflow][order_id={order.id}][action=ACTION_EXECUTED][step=payment_confirmed]")
        self._audit_log(order, 'action_executed', order.workflow_status)

    def _trigger_invoicing(self, order):
        # Ejecutar UseCase desacoplado de Nubefact.
        # CreateInvoiceUseCase es el punto de inyección para Fase 2.
        self.logger.info(f"[OrderWorkflow][order_id={order.id}][action=INVOICING_TRIGGERED][status=pending]")
        self._audit_log(order, 'invoicing_triggered', order.workflow_status)
        # Usar usecase inyectable (para tests) o crear uno nuevo (producción)
        usecase = self.create_invoice_usecase or CreateInvoiceUseCase()
        usecase.execute(order)

    def _audit_log(self, order, action, status, metadata=None):
        # Registrar en auditoría persistente (no solo logs efímeros).
        # Metadata puede incluir detalles contextuales (errores, retry counts, etc).
        try:
            OrderWorkflowLog.objects.create(
                organization=order.organization,
                order=order,
                action=action,
                status=status,
                metadata=metadata or {}
            )
        except Exception as e:
            # No romper workflow si auditoría falla.
            self.logger.warning(
                f"[OrderWorkflow][order_id={order.id}][action=AUDIT_LOG_FAILED][error={str(e)}]"
            )

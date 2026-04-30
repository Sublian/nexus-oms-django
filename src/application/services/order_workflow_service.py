# Único punto de orquestación para el flujo post-pago de una orden.
# No usar signals ni lógica en modelos — toda la magia va aquí.
# Fase futura: añadir invoicing (Nubefact) e inventory como pasos adicionales.
from src.domain.models.order_constants import OrderStatus


class OrderWorkflowService:

    def __init__(self, logger):
        self.logger = logger

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

        # 3. Pasos del flujo — añadir aquí en fases futuras (invoicing, inventory)
        self._log_order_paid(order)
        self._trigger_invoicing(order)

        # 4. Marcar persistente — se guarda en el order.save() del caller
        order.workflow_processed = True

        self.logger.info(f"[OrderWorkflow][order_id={order.id}][action=END]")

    def _log_order_paid(self, order):
        # Fase 1: solo logging. Fase 2: aquí irá llamada a Nubefact.
        self.logger.info(f"[OrderWorkflow][order_id={order.id}][action=ACTION_EXECUTED][step=payment_confirmed]")

    def _trigger_invoicing(self, order):
        # Placeholder: Fase 2 enchufará Nubefact aquí sin romper el diseño.
        # Por ahora solo registra la intención de invoicing.
        self.logger.info(f"[OrderWorkflow][order_id={order.id}][action=INVOICING_TRIGGERED][status=pending]")

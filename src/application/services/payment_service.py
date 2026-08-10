import logging
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone

from src.domain.models import Order, Payment
from src.domain.models.config import PaymentFeeConfig
from src.domain.models.order_constants import OrderStatus
from src.application.providers.factory import get_payment_provider
from src.application.services.order_workflow_service import OrderWorkflowService
from src.infrastructure.multitenancy.context import TenantContextManager


class PaymentServiceError(Exception):
    """Error de negocio con mensaje seguro para exponer al cliente."""

    def __init__(self, message, code='payment_error', http_status=400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.http_status = http_status


class PaymentTransitionNotAllowedError(PaymentServiceError):
    def __init__(self, order_status):
        super().__init__(
            f"Transición de estado no permitida desde {order_status} hacia PAID.",
            code='transition_not_allowed',
            http_status=400,
        )


class PaymentAlreadyExistsError(PaymentServiceError):
    def __init__(self):
        super().__init__(
            "Ya existe un registro de pago asociado a este pedido.",
            code='duplicate',
            http_status=409,
        )


class PaymentService:
    """
    Orquesta el ciclo de vida de un pago contra la pasarela.

      pending → approved  (la orden pasa a PAID + workflow post-pago)
              → declined  (la orden permanece PENDING; permite reintentar)
              → pending   (transferencia/Yape — se confirma con confirm_payment)

    Centraliza el cálculo de comisión (PaymentFeeConfig), antes duplicado en
    las vistas API/web y en seed_data. La comisión la asume la empresa: el
    total de la orden no cambia y net_amount = amount - fee_amount.
    """

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger('payment_service')

    # ── Pago inicial ─────────────────────────────────────────────────────────

    @transaction.atomic
    def process_payment(self, order, method, reference=None):
        method = (method or '').upper()
        if method not in Payment.PaymentMethod.values:
            raise PaymentServiceError(
                f"Método de pago inválido: {method}. Válidos: {Payment.PaymentMethod.values}",
                code='invalid_method',
            )

        # F1: tareas/scripts no pasan por el middleware → el contexto de tenant
        # se autogestiona desde la orden. Sin esto, Payment/Order.objects
        # devuelven .none() (fail-safe) y el flujo rompe silenciosamente.
        with TenantContextManager(order.organization_id):
            # F3: serializa pagos concurrentes por orden. Sin este lock, dos
            # POST simultáneos pasan el chequeo de duplicados → IntegrityError
            # (OneToOne de Payment.order) → 500.
            locked = Order.objects.select_for_update().get(pk=order.pk)

            existing = Payment.objects.filter(order=locked).first()
            if existing:
                if existing.status in (Payment.Status.PENDING, Payment.Status.APPROVED, Payment.Status.REFUNDED):
                    raise PaymentAlreadyExistsError()
                # Declined/failed → el cliente reintenta: se descarta el intento fallido
                existing.delete()

            if OrderStatus.PAID not in OrderStatus.VALID_TRANSITIONS.get(locked.status, []):
                raise PaymentTransitionNotAllowedError(locked.status)

            fee_rate = PaymentFeeConfig.get_rate(locked.organization, method)
            fee = (
                locked.total_amount * fee_rate / Decimal('100')
            ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            payment = Payment.objects.create(
                organization=locked.organization,
                order=locked,
                method=method,
                amount=locked.total_amount,
                fee_rate=fee_rate,
                fee_amount=fee,
                transaction_reference=(reference or '').strip() or None,
                status=Payment.Status.PENDING,
            )

            result = self._call_provider('process', payment)
            self._apply_result(payment, locked, result)

            # El re-fetch con lock trabaja sobre una instancia distinta (locked);
            # sincroniza el objeto del caller para que vea el estado final.
            order.refresh_from_db()
            return payment, result

    # ── Confirmación de un pago pendiente ────────────────────────────────────

    @transaction.atomic
    def confirm_payment(self, payment, order=None):
        """Consulta la pasarela; si aprueba, marca la orden PAID. Idempotente."""
        order = order or payment.order

        if payment.status != Payment.Status.PENDING:
            self.logger.info(
                f"[PaymentService][payment_id={payment.id}]"
                f"[action=SKIP][reason=not_pending][status={payment.status}]"
            )
            return payment, {'status': payment.status, 'skipped': True}

        # F1: misma razón que en process_payment — el worker de sync corre sin contexto.
        with TenantContextManager(order.organization_id):
            result = self._call_provider('status', payment)
            self._apply_result(payment, order, result)
        return payment, result

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _apply_result(self, payment, order, result):
        status = result.get('status')
        external_id = result.get('external_id')

        if external_id:
            payment.external_reference = external_id

        if status == 'approved':
            payment.status = Payment.Status.APPROVED
            payment.approved_at = timezone.now()
            payment.error_message = None
            payment.save(update_fields=['status', 'external_reference', 'approved_at', 'error_message'])
            self._mark_order_paid(order)
        elif status == 'declined':
            payment.status = Payment.Status.DECLINED
            payment.error_message = result.get('error') or 'El pago fue rechazado por la pasarela.'
            payment.save(update_fields=['status', 'external_reference', 'error_message'])
            self.logger.info(
                f"[PaymentService][payment_id={payment.id}][order_id={order.id}]"
                f"[action=DECLINED][error={payment.error_message}]"
            )
        else:  # pending
            payment.save(update_fields=['status', 'external_reference'])

    def _mark_order_paid(self, order):
        # F2: la orden pudo haber cambiado de estado desde que el pago entró en
        # 'pending' (ej: PENDING→CANCELLED con stock ya restaurado). Solo se
        # promueve a PAID si la transición es válida; si no, se registra la
        # anomalía y la orden NO se modifica (el pago sí queda 'approved').
        # El guard también hace idempotente el workflow ante doble confirmación
        # (order ya PAID → VALID_TRANSITIONS[PAID] no incluye PAID → skip).
        if OrderStatus.PAID not in OrderStatus.VALID_TRANSITIONS.get(order.status, []):
            self.logger.error(
                f"[PaymentService][order_id={order.id}][action=ANOMALY]"
                f"[reason=order_not_payable][order_status={order.status}]"
                " Pago aprobado pero la orden no puede pasar a PAID; no se modifica."
            )
            return
        order.status = OrderStatus.PAID
        workflow = OrderWorkflowService(self.logger)
        workflow.handle_order_paid(order)
        order.save()

    def _call_provider(self, action, payment):
        config = PaymentFeeConfig.get_config(payment.organization)
        provider = get_payment_provider(config)

        if action == 'process':
            return provider.process_payment(payment)
        return provider.get_payment_status(payment)

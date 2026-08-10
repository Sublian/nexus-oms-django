import pytest
from decimal import Decimal

from src.domain.models import Order, Payment, PaymentFeeConfig
from src.domain.models.order_constants import OrderStatus
from src.application.services.payment_service import (
    PaymentService,
    PaymentServiceError,
    PaymentTransitionNotAllowedError,
    PaymentAlreadyExistsError,
)


@pytest.fixture
def pending_order(db, organization):
    return Order.objects.create(
        organization=organization,
        customer_name='Cliente Test',
        customer_email='cliente@test.com',
        status=OrderStatus.PENDING,
        subtotal=Decimal('100.00'),
        tax_amount=Decimal('18.00'),
        total_amount=Decimal('118.00'),
    )


@pytest.mark.django_db
class TestPaymentService:

    def test_cash_approved_and_order_paid(self, pending_order, organization):
        payment, result = PaymentService().process_payment(pending_order, 'CASH')

        pending_order.refresh_from_db()
        assert payment.status == Payment.Status.APPROVED
        assert payment.fee_amount == Decimal('0.00')
        assert pending_order.status == OrderStatus.PAID

    def test_card_fee_from_config_and_net_amount(self, pending_order, organization):
        payment, result = PaymentService().process_payment(pending_order, 'CARD', 'TXN-123')

        pending_order.refresh_from_db()
        assert payment.status == Payment.Status.APPROVED
        assert payment.fee_rate == Decimal('3.50')
        assert payment.fee_amount == Decimal('4.13')       # 118 * 3.5%
        assert payment.net_amount == Decimal('113.87')
        assert pending_order.status == OrderStatus.PAID

    def test_custom_fee_rate_respected(self, pending_order, organization):
        config = PaymentFeeConfig.get_config(organization)
        config.card_rate = 5.00
        config.save()

        payment, _ = PaymentService().process_payment(pending_order, 'CARD')
        assert payment.fee_amount == Decimal('5.90')       # 118 * 5%

    def test_wallet_fee_applied(self, pending_order, organization):
        payment, _ = PaymentService().process_payment(pending_order, 'WALLET', 'Yape 999')

        assert payment.status == Payment.Status.PENDING
        assert payment.fee_rate == Decimal('1.00')
        assert payment.fee_amount == Decimal('1.18')       # 118 * 1%
        pending_order.refresh_from_db()
        assert pending_order.status == OrderStatus.PENDING  # aún no pagado

    def test_card_declined_keeps_order_pending_and_allows_retry(self, pending_order, organization):
        payment, result = PaymentService().process_payment(pending_order, 'CARD', 'REJECT-1')

        assert payment.status == Payment.Status.DECLINED
        assert payment.error_message
        pending_order.refresh_from_db()
        assert pending_order.status == OrderStatus.PENDING

        # Reintento con otra tarjeta → aprobado
        payment2, _ = PaymentService().process_payment(pending_order, 'CARD', 'TXN-OK')
        assert payment2.status == Payment.Status.APPROVED
        pending_order.refresh_from_db()
        assert pending_order.status == OrderStatus.PAID

    def test_transfer_pending_then_confirmed(self, pending_order, organization):
        payment, result = PaymentService().process_payment(pending_order, 'TRANSFER', 'BCP-001')

        assert payment.status == Payment.Status.PENDING
        pending_order.refresh_from_db()
        assert pending_order.status == OrderStatus.PENDING

        payment, result = PaymentService().confirm_payment(payment, order=pending_order)
        assert payment.status == Payment.Status.APPROVED
        pending_order.refresh_from_db()
        assert pending_order.status == OrderStatus.PAID

    def test_confirm_payment_idempotent(self, pending_order, organization):
        payment, _ = PaymentService().process_payment(pending_order, 'CASH')
        assert payment.status == Payment.Status.APPROVED

        payment2, result = PaymentService().confirm_payment(payment, order=pending_order)
        assert payment2.status == Payment.Status.APPROVED
        assert result.get('skipped') is True

    def test_duplicate_approved_payment_rejected(self, pending_order, organization):
        PaymentService().process_payment(pending_order, 'CASH')

        with pytest.raises(PaymentAlreadyExistsError):
            PaymentService().process_payment(pending_order, 'CARD')

    def test_transition_not_allowed_from_draft(self, pending_order, organization):
        pending_order.status = OrderStatus.DRAFT
        pending_order.save()

        with pytest.raises(PaymentTransitionNotAllowedError):
            PaymentService().process_payment(pending_order, 'CASH')

    def test_invalid_method_rejected(self, pending_order, organization):
        with pytest.raises(PaymentServiceError):
            PaymentService().process_payment(pending_order, 'BITCOIN')

    def test_process_payment_works_without_tenant_context(self, pending_order, organization):
        """REGRESIÓN F1: process_payment debe autogestionar el contexto de tenant.

        Simula llamadas externas (tasks, scripts) donde el middleware no corrió.
        Sin el wrapper, Payment.objects / Order.objects devuelven .none() y el
        chequeo de duplicados y el lock fallan silenciosamente.
        """
        from src.infrastructure.multitenancy.context import clear_current_organization

        clear_current_organization()

        payment, _ = PaymentService().process_payment(pending_order, 'CASH')

        payment = Payment.all_objects.get(pk=payment.id)
        pending_order = Order.all_objects.get(pk=pending_order.id)
        assert payment.status == Payment.Status.APPROVED
        assert pending_order.status == OrderStatus.PAID

    def test_confirm_approved_payment_does_not_revive_cancelled_order(
        self, pending_order, organization
    ):
        """REGRESIÓN F2: una transferencia pendiente que aprueba DESPUÉS de cancelar
        la orden no debe revivirla a PAID.

        El stock ya fue restaurado al cancelar; revivir la orden crearía un
        cobro + inventario inconsistente. La pasarela cobró (payment approved),
        pero la orden permanece CANCELLED.
        """
        payment, _ = PaymentService().process_payment(pending_order, 'TRANSFER', 'BCP-002')
        assert payment.status == Payment.Status.PENDING

        pending_order.status = OrderStatus.CANCELLED
        pending_order.save()

        payment, result = PaymentService().confirm_payment(payment, order=pending_order)

        payment.refresh_from_db()
        pending_order.refresh_from_db()
        assert payment.status == Payment.Status.APPROVED
        assert pending_order.status == OrderStatus.CANCELLED

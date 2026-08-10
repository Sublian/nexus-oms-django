"""
Tests para sync_pending_payments_task y sync_single_payment_task.

Cubre: fan-out, idempotencia (skip no-pending), confirmación de transferencia/Yape.
"""
import pytest
from decimal import Decimal

from src.domain.models import Order, Payment
from src.domain.models.order_constants import OrderStatus
from src.domain.tasks.payment_tasks import (
    sync_single_payment_task,
    sync_pending_payments_task,
)


@pytest.fixture
def pending_order(db, organization):
    return Order.objects.create(
        organization=organization,
        customer_name='Test Client',
        customer_email='test@nexus.com',
        status=OrderStatus.PENDING,
        subtotal=Decimal('100.00'),
        tax_amount=Decimal('18.00'),
        total_amount=Decimal('118.00'),
    )


def _make_payment(organization, order, status=Payment.Status.PENDING, method='TRANSFER'):
    return Payment.objects.create(
        organization=organization,
        order=order,
        method=method,
        amount=order.total_amount,
        status=status,
        transaction_reference='BCP-001',
    )


@pytest.mark.django_db
class TestSyncSinglePaymentTask:

    def test_pending_transfer_confirmed_and_order_paid(self, organization, pending_order):
        payment = _make_payment(organization, pending_order)

        result = sync_single_payment_task.delay(payment.id)

        payment.refresh_from_db()
        pending_order.refresh_from_db()
        assert result.result == Payment.Status.APPROVED
        assert payment.status == Payment.Status.APPROVED
        assert pending_order.status == OrderStatus.PAID

    def test_not_pending_is_skipped(self, organization, pending_order):
        payment = _make_payment(organization, pending_order, status=Payment.Status.APPROVED)

        result = sync_single_payment_task.delay(payment.id)

        pending_order.refresh_from_db()
        assert pending_order.status == OrderStatus.PENDING   # no cambió
        assert result.result is None

    def test_unknown_payment_returns_none(self, organization):
        result = sync_single_payment_task.delay(999999)
        assert result.result is None

    def test_confirm_error_is_logged_and_reraises(self, organization, pending_order, mocker):
        payment = _make_payment(organization, pending_order)

        mocker.patch(
            'src.application.services.payment_service.PaymentService.confirm_payment',
            side_effect=RuntimeError('pasarela caída'),
        )

        with pytest.raises(RuntimeError):
            sync_single_payment_task.delay(payment.id)

        payment.refresh_from_db()
        pending_order.refresh_from_db()
        assert payment.status == Payment.Status.PENDING
        assert pending_order.status == OrderStatus.PENDING

    def test_lock_failure_is_logged_and_reraises(self, organization, pending_order, mocker):
        _make_payment(organization, pending_order)

        mocker.patch(
            'src.domain.models.Payment.all_objects.select_for_update',
            side_effect=Exception('lock timeout'),
        )

        with pytest.raises(Exception, match='lock timeout'):
            sync_single_payment_task.delay(pending_order.id)

    def test_confirm_without_tenant_context_uses_payment_organization(
        self, organization, pending_order
    ):
        """REGRESIÓN F1: el worker de Celery corre en un proceso SIN contexto tenant.

        El test previo pasaba solo porque el eager task corría en el mismo hilo
        donde la fixture `organization` había seteado el contexto. En producción
        _claim_workflow_lock haría Order.objects.none().get() → DoesNotExist y el
        pago quedaría 'pending' reintentándose cada 60s para siempre.
        """
        from src.infrastructure.multitenancy.context import clear_current_organization

        payment = _make_payment(organization, pending_order)

        clear_current_organization()

        result = sync_single_payment_task.delay(payment.id)

        payment = Payment.all_objects.get(pk=payment.id)
        pending_order = Order.all_objects.get(pk=pending_order.id)
        assert result.result == Payment.Status.APPROVED
        assert payment.status == Payment.Status.APPROVED
        assert pending_order.status == OrderStatus.PAID
        assert pending_order.workflow_processed is True


@pytest.mark.django_db
class TestSyncPendingPaymentsTask:

    def test_fanout_dispatches_only_pending(self, organization, mocker):
        pending_order = Order.objects.create(
            organization=organization, customer_name='A', customer_email='a@test.com',
            status=OrderStatus.PENDING, total_amount=Decimal('100.00'),
        )
        approved_order = Order.objects.create(
            organization=organization, customer_name='B', customer_email='b@test.com',
            status=OrderStatus.PENDING, total_amount=Decimal('100.00'),
        )
        _make_payment(organization, pending_order, status=Payment.Status.PENDING)
        _make_payment(organization, approved_order, status=Payment.Status.APPROVED, method='CASH')

        mock_delay = mocker.patch('src.domain.tasks.payment_tasks.sync_single_payment_task.delay')

        count = sync_pending_payments_task.delay()

        assert count.result == 1
        assert mock_delay.call_count == 1

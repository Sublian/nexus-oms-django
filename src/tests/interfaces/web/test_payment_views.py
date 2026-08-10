import pytest
from decimal import Decimal

from django.urls import reverse

from src.domain.models import Order, Payment
from src.domain.models.order_constants import OrderStatus


@pytest.fixture
def pending_order(db, organization):
    return Order.objects.create(
        organization=organization,
        customer_name='Cliente Web',
        customer_email='web@test.com',
        status=OrderStatus.PENDING,
        subtotal=Decimal('100.00'),
        tax_amount=Decimal('18.00'),
        total_amount=Decimal('118.00'),
    )


def _pay_url(organization, order):
    return reverse('web:order_pay', kwargs={'org_slug': organization.slug, 'order_id': order.id})


@pytest.mark.django_db
class TestPayModalWeb:

    def test_pay_modal_get_renders_with_fee_rates(self, logged_in_client, organization, pending_order):
        url = _pay_url(organization, pending_order)
        response = logged_in_client.get(url)

        assert response.status_code == 200
        content = response.content.decode()
        assert 'fees' in content
        assert '3.5' in content          # tasa CARD del config por defecto

    def test_pay_cash_marks_order_paid(self, logged_in_client, organization, pending_order):
        url = _pay_url(organization, pending_order)
        response = logged_in_client.post(url, {'method': 'CASH'})

        assert response.status_code == 200
        pending_order.refresh_from_db()
        assert pending_order.status == OrderStatus.PAID
        payment = pending_order.payment
        assert payment.status == Payment.Status.APPROVED
        assert payment.fee_amount == Decimal('0.00')

    def test_pay_card_approved_with_fee(self, logged_in_client, organization, pending_order):
        url = _pay_url(organization, pending_order)
        response = logged_in_client.post(url, {'method': 'CARD', 'reference': 'TXN-001'})

        assert response.status_code == 200
        pending_order.refresh_from_db()
        payment = pending_order.payment
        assert payment.status == Payment.Status.APPROVED
        assert payment.fee_amount == Decimal('4.13')

    def test_pay_card_declined(self, logged_in_client, organization, pending_order):
        url = _pay_url(organization, pending_order)
        response = logged_in_client.post(url, {'method': 'CARD', 'reference': 'REJECT-1'})

        assert response.status_code == 400
        pending_order.refresh_from_db()
        assert pending_order.status == OrderStatus.PENDING
        assert not hasattr(pending_order, 'payment') or pending_order.payment.status == Payment.Status.DECLINED

    def test_pay_wallet_pending_confirmation(self, logged_in_client, organization, pending_order):
        url = _pay_url(organization, pending_order)
        response = logged_in_client.post(url, {'method': 'WALLET', 'reference': 'Yape 999'})

        assert response.status_code == 200
        content = response.content.decode()
        assert 'pendiente' in content.lower()
        pending_order.refresh_from_db()
        assert pending_order.status == OrderStatus.PENDING
        assert pending_order.payment.status == Payment.Status.PENDING

    def test_pay_transition_not_allowed(self, logged_in_client, organization, pending_order):
        pending_order.status = OrderStatus.PAID
        pending_order.save()

        url = _pay_url(organization, pending_order)
        response = logged_in_client.post(url, {'method': 'CASH'})
        assert response.status_code == 400


@pytest.mark.django_db
class TestConfirmPaymentWeb:

    def test_confirm_pending_payment(self, logged_in_client, organization, pending_order):
        pay_url = _pay_url(organization, pending_order)
        logged_in_client.post(pay_url, {'method': 'TRANSFER', 'reference': 'BCP-001'})

        confirm_url = reverse('web:order_confirm_payment', kwargs={
            'org_slug': organization.slug, 'order_id': pending_order.id,
        })
        response = logged_in_client.post(confirm_url)

        assert response.status_code == 200
        pending_order.refresh_from_db()
        assert pending_order.status == OrderStatus.PAID
        assert pending_order.payment.status == Payment.Status.APPROVED

    def test_confirm_when_no_pending_payment(self, logged_in_client, organization, pending_order):
        confirm_url = reverse('web:order_confirm_payment', kwargs={
            'org_slug': organization.slug, 'order_id': pending_order.id,
        })
        response = logged_in_client.post(confirm_url)
        assert response.status_code == 400

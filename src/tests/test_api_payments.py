import pytest
from decimal import Decimal

from django.urls import reverse
from rest_framework import status

from src.domain.models import Order, Payment
from src.domain.models.order_constants import OrderStatus


@pytest.fixture
def pending_order(db, organization):
    return Order.objects.create(
        organization=organization,
        customer_name='Cliente API',
        customer_email='api@test.com',
        status=OrderStatus.PENDING,
        subtotal=Decimal('100.00'),
        tax_amount=Decimal('18.00'),
        total_amount=Decimal('118.00'),
    )


@pytest.mark.django_db
class TestOrderPayAPI:

    def test_pay_card_approved(self, auth_api_client, pending_order):
        url = reverse('order-pay', kwargs={'pk': pending_order.pk})
        response = auth_api_client.post(url, {'method': 'CARD', 'reference': 'TXN-001'}, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['payment_status'] == Payment.Status.APPROVED
        assert response.data['status'] == OrderStatus.PAID
        assert response.data['fee_applied'] == 4.13

        pending_order.refresh_from_db()
        assert pending_order.status == OrderStatus.PAID

    def test_pay_wallet_pending(self, auth_api_client, pending_order):
        url = reverse('order-pay', kwargs={'pk': pending_order.pk})
        response = auth_api_client.post(url, {'method': 'WALLET', 'reference': 'Yape 999'}, format='json')

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.data['payment_status'] == Payment.Status.PENDING
        assert response.data['status'] == OrderStatus.PENDING

        pending_order.refresh_from_db()
        assert pending_order.status == OrderStatus.PENDING

    def test_pay_transfer_accepted_by_serializer(self, auth_api_client, pending_order):
        """TRANSFER ya es válido en el serializer (antes solo CASH/CARD)."""
        url = reverse('order-pay', kwargs={'pk': pending_order.pk})
        response = auth_api_client.post(url, {'method': 'TRANSFER', 'reference': 'BCP-001'}, format='json')

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.data['payment_status'] == Payment.Status.PENDING

    def test_pay_card_declined(self, auth_api_client, pending_order):
        url = reverse('order-pay', kwargs={'pk': pending_order.pk})
        response = auth_api_client.post(url, {'method': 'CARD', 'reference': 'REJECT-99'}, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['payment_status'] == Payment.Status.DECLINED
        pending_order.refresh_from_db()
        assert pending_order.status == OrderStatus.PENDING

    def test_pay_invalid_method(self, auth_api_client, pending_order):
        url = reverse('order-pay', kwargs={'pk': pending_order.pk})
        response = auth_api_client.post(url, {'method': 'BITCOIN'}, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_pay_duplicate_conflict(self, auth_api_client, pending_order):
        url = reverse('order-pay', kwargs={'pk': pending_order.pk})
        auth_api_client.post(url, {'method': 'CASH'}, format='json')

        response = auth_api_client.post(url, {'method': 'CARD'}, format='json')
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_pay_not_allowed_from_paid(self, auth_api_client, pending_order):
        pending_order.status = OrderStatus.PAID
        pending_order.save()

        url = reverse('order-pay', kwargs={'pk': pending_order.pk})
        response = auth_api_client.post(url, {'method': 'CASH'}, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestOrderPaymentStatusAPI:

    def test_payment_status_not_found(self, auth_api_client, pending_order):
        url = reverse('order-payment', kwargs={'pk': pending_order.pk})
        response = auth_api_client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_payment_status_after_wallet_pay(self, auth_api_client, pending_order):
        pay_url = reverse('order-pay', kwargs={'pk': pending_order.pk})
        auth_api_client.post(pay_url, {'method': 'WALLET', 'reference': 'Yape 999'}, format='json')

        url = reverse('order-payment', kwargs={'pk': pending_order.pk})
        response = auth_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['method'] == 'WALLET'
        assert response.data['payment_status'] == Payment.Status.PENDING
        assert response.data['fee_amount'] == 1.18


@pytest.mark.django_db
class TestOrderConfirmPaymentAPI:

    def test_confirm_pending_payment(self, auth_api_client, pending_order):
        pay_url = reverse('order-pay', kwargs={'pk': pending_order.pk})
        auth_api_client.post(pay_url, {'method': 'TRANSFER', 'reference': 'BCP-001'}, format='json')

        url = reverse('order-confirm-payment', kwargs={'pk': pending_order.pk})
        response = auth_api_client.post(url, {}, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['payment_status'] == Payment.Status.APPROVED
        assert response.data['status'] == OrderStatus.PAID

        pending_order.refresh_from_db()
        assert pending_order.status == OrderStatus.PAID

    def test_confirm_when_no_payment(self, auth_api_client, pending_order):
        url = reverse('order-confirm-payment', kwargs={'pk': pending_order.pk})
        response = auth_api_client.post(url, {}, format='json')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_confirm_when_not_pending(self, auth_api_client, pending_order):
        pay_url = reverse('order-pay', kwargs={'pk': pending_order.pk})
        auth_api_client.post(pay_url, {'method': 'CASH'}, format='json')

        url = reverse('order-confirm-payment', kwargs={'pk': pending_order.pk})
        response = auth_api_client.post(url, {}, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

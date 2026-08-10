"""
Test para la migración 0019 (backfill de fee_amount).

Regresión F4: la migración 0018 backfilleó status/approved_at/fee_rate pero NO
fee_amount, dejando los pagos aprobados históricos con fee_amount=0 → los
reportes de finanzas calculaban net_amount=amount (sin comisión).

El test invoca la función de la migración directamente sobre el modelo vivo
(schema_editor no se usa en el backfill).
"""
from decimal import Decimal

import pytest
from django.apps import apps as django_apps

from src.domain.models import Payment, Order
from src.domain.models.order_constants import OrderStatus


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
class TestMigration0019BackfillFeeAmount:

    def _make_approved_payment(self, organization, order, **kwargs):
        defaults = {
            'organization': organization,
            'order': order,
            'method': 'CARD',
            'amount': Decimal('118.00'),
            'fee_rate': Decimal('3.50'),
            'fee_amount': Decimal('0.00'),
            'status': Payment.Status.APPROVED,
        }
        defaults.update(kwargs)
        return Payment.objects.create(**defaults)

    def test_backfills_fee_amount_for_approved_payments(self, organization, pending_order):
        payment = self._make_approved_payment(organization, pending_order)

        # Import del módulo 0019 por nombre de archivo
        import importlib
        module = importlib.import_module('src.domain.migrations.0019_backfill_fee_amount')
        module.backfill_fee_amount(django_apps, None)

        payment.refresh_from_db()
        assert payment.fee_amount == Decimal('4.13')   # 118 * 3.5%

    def test_skips_payments_without_fee_rate(self, organization, pending_order):
        payment = self._make_approved_payment(
            organization, pending_order, method='CASH', fee_rate=Decimal('0.00'),
        )

        import importlib
        module = importlib.import_module('src.domain.migrations.0019_backfill_fee_amount')
        module.backfill_fee_amount(django_apps, None)

        payment.refresh_from_db()
        assert payment.fee_amount == Decimal('0.00')

    def test_skips_non_approved_payments(self, organization, pending_order):
        payment = self._make_approved_payment(
            organization, pending_order, status=Payment.Status.PENDING,
        )

        import importlib
        module = importlib.import_module('src.domain.migrations.0019_backfill_fee_amount')
        module.backfill_fee_amount(django_apps, None)

        payment.refresh_from_db()
        assert payment.fee_amount == Decimal('0.00')

# Backfill de fee_amount para pagos aprobados históricos.
#
# La migración 0018 backfilleó status/approved_at/fee_rate pero NO fee_amount,
# dejando fee_amount=0 en los pagos previos a PaymentService → los reportes de
# finanzas calculaban net_amount = amount (sin descontar la comisión).
# Recalcula fee_amount = amount * fee_rate / 100 solo donde corresponde.
from decimal import ROUND_HALF_UP, Decimal

from django.db import migrations


def backfill_fee_amount(apps, schema_editor):
    Payment = apps.get_model('domain', 'Payment')
    # _base_manager: Manager plano sin filtrado. En modelos históricos de
    # migración solo se preserva el manager por defecto (TenantManager), y este
    # devuelve .none() sin contexto de tenant → el backfill sería un no-op.
    pending = (
        Payment._base_manager
        .filter(status='approved', fee_rate__gt=0, fee_amount=0)
        .iterator()
    )
    for payment in pending:
        payment.fee_amount = (
            payment.amount * payment.fee_rate / Decimal('100')
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        payment.save(update_fields=['fee_amount'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('domain', '0018_backfill_payment_status'),
    ]

    operations = [
        migrations.RunPython(backfill_fee_amount, noop),
    ]

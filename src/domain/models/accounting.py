from django.db import models
from django.utils import timezone

from src.infrastructure.models import TenantModel


class AccountingEntry(TenantModel):
    """
    Asiento contable generado cuando una factura es aceptada por SUNAT.

    Regla crítica: solo puede existir cuando Order.invoice_status == 'accepted'.
    La restricción se enforce en la capa de aplicación (UseCase/task), no aquí.

    Diseño orientado a:
    - libro diario futuro
    - ledger por cuenta
    - exportación ERP
    - reportes financieros por período

    Un Order puede tener como máximo un AccountingEntry (OneToOneField).
    Garantía de idempotencia: si el proceso es reintentado, get_or_create
    detecta la entrada existente y no la duplica.
    """

    class EntryType(models.TextChoices):
        SALE       = 'sale',       'Venta'
        RETURN     = 'return',     'Devolución'
        ADJUSTMENT = 'adjustment', 'Ajuste Manual'

    order = models.OneToOneField(
        'domain.Order',
        on_delete=models.PROTECT,
        related_name='accounting_entry',
        help_text='Orden origen — OneToOne garantiza un solo asiento por factura aceptada',
    )
    entry_type = models.CharField(
        max_length=20,
        choices=EntryType.choices,
        default=EntryType.SALE,
    )
    invoice_external_id = models.CharField(
        max_length=255,
        help_text='Snapshot del ID externo Nubefact al momento de generar el asiento',
    )
    amount_gross = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text='Total bruto de la factura (incluye impuestos)',
    )
    amount_tax = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text='Monto de impuestos (IGV)',
    )
    amount_net = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text='Base imponible (sin impuestos)',
    )
    currency = models.CharField(
        max_length=3,
        default='PEN',
        help_text='Código ISO 4217 de la moneda',
    )
    entry_date = models.DateField(
        default=timezone.localdate,
        help_text='Fecha contable del asiento — normalmente la fecha de aceptación SUNAT',
    )
    notes = models.TextField(
        null=True,
        blank=True,
        help_text='Notas internas del asiento (ajustes manuales, referencias, etc.)',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Asiento Contable'
        verbose_name_plural = 'Asientos Contables'
        indexes = [
            models.Index(fields=['organization', 'entry_date']),
            models.Index(fields=['organization', 'entry_type']),
        ]

    def __str__(self):
        return f"AccountingEntry order_id={self.order_id} [{self.entry_type}] {self.amount_gross} {self.currency}"


class AccountingEntryLine(models.Model):
    """
    Línea de un asiento contable (partida doble).

    Invariante: para cada AccountingEntry, sum(debit) == sum(credit).
    Se verifica en la capa de aplicación al crear el asiento.

    account_code referencia el plan de cuentas futuro (ChartOfAccounts).
    Por ahora se usa como campo libre hasta implementar el catálogo.
    """

    entry = models.ForeignKey(
        AccountingEntry,
        on_delete=models.CASCADE,
        related_name='lines',
    )
    account_code = models.CharField(
        max_length=20,
        help_text='Código de cuenta contable (placeholder — referenciará ChartOfAccounts en futuro)',
    )
    description = models.CharField(
        max_length=255,
        help_text='Descripción de la partida',
    )
    debit = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        help_text='Monto débito de la partida',
    )
    credit = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
        help_text='Monto crédito de la partida',
    )

    class Meta:
        verbose_name = 'Línea de Asiento Contable'
        verbose_name_plural = 'Líneas de Asiento Contable'

    def __str__(self):
        return f"Line [{self.account_code}] D:{self.debit} C:{self.credit}"

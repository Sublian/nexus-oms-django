# src\domain\models.py

from decimal import Decimal

from django.db import models

from src.infrastructure.models import TenantModel


class TaxConfiguration(TenantModel):
    name = models.CharField(max_length=50) # Ej: "IGV Perú", "IVA España"
    rate = models.DecimalField(max_digits=5, decimal_places=2) # Ej: 18.00
    is_default = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.rate}%)"
    
class SalesReport(TenantModel):
    generated_at = models.DateTimeField(auto_now_add=True)
    total_sales = models.DecimalField(max_digits=15, decimal_places=2)
    order_count = models.IntegerField()
    data = models.JSONField() # Guardaremos el desglose aquí

    def __str__(self):
        return f"Reporte {self.generated_at} - {self.organization.name}"
    
class CashReconciliation(TenantModel):
    opened_at = models.DateTimeField()
    closed_at = models.DateTimeField(auto_now_add=True)
    
    # Lo que el sistema calculó
    expected_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # Lo que el cajero contó físicamente
    actual_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Calculado: actual - expected
    difference = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    
    notes = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        # Lógica de negocio: Calcular diferencia antes de guardar
        self.difference = self.actual_amount - self.expected_amount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Arqueo {self.organization.name} - {self.closed_at.date()}"


class PaymentFeeConfig(TenantModel):
    """
    Tasas de comisión por método de pago (asumidas por la empresa, no por el cliente).

    Se aplican sobre el total de la orden y se descuentan del ingreso neto
    (Payment.net_amount). Snapshot de fee_rate se guarda en cada Payment al
    momento de procesarlo — cambiar la tasa no altera pagos históricos.
    """
    METHOD_CODES = ('CASH', 'CARD', 'TRANSFER', 'WALLET')

    cash_rate     = models.DecimalField(max_digits=5, decimal_places=2, default=0,    help_text="% comisión efectivo")
    card_rate     = models.DecimalField(max_digits=5, decimal_places=2, default=3.50, help_text="% comisión tarjeta (ej: Niubiz/Izipay)")
    transfer_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0,    help_text="% comisión transferencia bancaria")
    wallet_rate   = models.DecimalField(max_digits=5, decimal_places=2, default=1.00, help_text="% comisión billetera digital (Yape/Plin)")
    provider_type = models.CharField(
        max_length=20,
        choices=[('mock', 'Mock (desarrollo)'), ('izipay', 'Izipay (producción)')],
        default='mock',
        help_text="Proveedor activo de pasarela de pagos",
    )
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuración de Comisiones de Pago"
        verbose_name_plural = "Configuraciones de Comisiones de Pago"

    def __str__(self):
        return f"Fees {self.organization.name} — CARD {self.card_rate}%"

    def rate_for(self, method: str):
        """Tasa (%) para un código de método de pago (CASH|CARD|TRANSFER|WALLET)."""
        rate = {
            'CASH': self.cash_rate,
            'CARD': self.card_rate,
            'TRANSFER': self.transfer_rate,
            'WALLET': self.wallet_rate,
        }[method]
        return Decimal(str(rate))

    @classmethod
    def get_rate(cls, organization, method: str):
        """Tasa (%) para el método, con defaults si no hay config registrada."""
        config = cls.objects.filter(organization=organization).first()
        if not config:
            config = cls(organization=organization)
        return config.rate_for(method)

    @classmethod
    def get_config(cls, organization):
        """Retorna la config del tenant, creándola con defaults si no existe."""
        config, _ = cls.objects.get_or_create(organization=organization)
        return config


class CompanyInvoiceConfig(TenantModel):
    # Configuración de facturación Nubefact por tenant
    # Cada organización tiene su endpoint, token y credenciales aisladas
    api_base_url = models.URLField(
        help_text="URL base de API Nubefact (ej: https://api.nubefact.com/api)"
    )
    endpoint_url = models.CharField(
        max_length=255,
        help_text="Endpoint específico (ej: invoices, documents)"
    )
    token = models.CharField(
        max_length=255,
        help_text="Token/API key para autenticación"
    )
    enabled = models.BooleanField(
        default=True,
        help_text="Si está deshabilitado, usa MockNubefactClient"
    )
    provider_type = models.CharField(
        max_length=20,
        choices=[('mock', 'Mock (desarrollo)'), ('nubefact', 'Nubefact (producción)')],
        default='mock',
        help_text="Proveedor activo: mock (desarrollo) | nubefact (producción)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuración de Facturación"
        verbose_name_plural = "Configuraciones de Facturación"

    def __str__(self):
        return f"Config Facturación - {self.organization.name}"

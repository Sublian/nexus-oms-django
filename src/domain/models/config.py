# src\domain\models.py

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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuración de Facturación"
        verbose_name_plural = "Configuraciones de Facturación"

    def __str__(self):
        return f"Config Facturación - {self.organization.name}"

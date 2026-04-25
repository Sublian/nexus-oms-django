import uuid
from django.db import models
from src.infrastructure.models import TenantModel

class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True) # Para la URL: nexus.com/empresa-a
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    telegram_enabled = models.BooleanField(default=False)
    whatsapp_enabled = models.BooleanField(default=False)
    admin_email = models.EmailField()
    primary_color = models.CharField(max_length=7, default="#000000") # Color en formato hexadecimal
    secondary_color = models.CharField(max_length=7, default="#FFFFFF") # Color en formato hexadecimal
    logo_image = models.ImageField(upload_to='organization_logos/', blank=True, null=True) # Imagen del logo de la empresa
    dashboard_batch_size = models.PositiveIntegerField(default=10, help_text="Registros por página en el dashboard")
    currency_symbol = models.CharField(max_length=5, default="$")
    ruc = models.CharField(max_length=11, default="00000000000")
    address = models.TextField(default="Dirección por defecto")
    default_shipping_fee = models.DecimalField(
        max_digits=8, decimal_places=2, default=10.00,
        help_text="Costo de envío por defecto (S/)"
    )

    def __str__(self):
        return self.name
   

class Client(TenantModel):
    DOCUMENT_TYPES = (
        ('DNI', 'DNI'),
        ('RUC', 'RUC'),
        ('CE', 'Carnet de Extranjería'),
        ('PAS', 'Pasaporte'),
    )

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='clients')
    document_type = models.CharField(max_length=5, choices=DOCUMENT_TYPES)
    document_number = models.CharField(max_length=15)
    name = models.CharField(max_length=255, verbose_name="Nombre o Razón Social")
    address = models.TextField(blank=True, null=True, verbose_name="Dirección")
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('organization', 'document_number') # Evitar duplicados por tenant
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.document_number} - {self.name}"   
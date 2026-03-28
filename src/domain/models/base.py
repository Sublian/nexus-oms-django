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

    def __str__(self):
        return self.name
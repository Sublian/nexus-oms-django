from django.db import models
from .multitenancy.managers import TenantManager

class TenantModel(models.Model):
    organization = models.ForeignKey(
        'domain.Organization', 
        on_delete=models.CASCADE,
        related_name="%(class)s_items"
    )
    
    # Usamos el manager personalizado para el filtrado automático
    objects = TenantManager()
    # Mantenemos el manager original por si necesitamos ver todo (admin, por ejemplo)
    all_objects = models.Manager()

    class Meta:
        abstract = True
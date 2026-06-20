from django.db import models
from .multitenancy.managers import TenantManager, TenantQuerySet


class TenantModel(models.Model):
    organization = models.ForeignKey(
        'domain.Organization',
        on_delete=models.CASCADE,
        related_name="%(class)s_items"
    )

    # Automatic filtering manager (respects context, fail-safe empty if no context)
    objects = TenantManager.from_queryset(TenantQuerySet)()

    # Unfiltered access for admin/audit (bypass tenant filtering)
    unfiltered = models.Manager()
    # Backward compatibility alias
    all_objects = models.Manager()

    class Meta:
        abstract = True
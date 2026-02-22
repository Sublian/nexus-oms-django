from django.db import models
from .thread_local import get_current_organization

class TenantManager(models.Manager):
    def get_queryset(self):
        org_id = get_current_organization()
        queryset = super().get_queryset()
        if org_id:
            return queryset.filter(organization_id=org_id)
        return queryset
from django.db import models
from .context import get_current_organization


class TenantQuerySet(models.QuerySet):
    """QuerySet with automatic tenant filtering."""

    def filter_by_context(self):
        """Filter by current organization context if set."""
        org_id = get_current_organization()
        if org_id:
            return self.filter(organization_id=org_id)
        return self.none()


class TenantManager(models.Manager):
    """Manager with automatic organization filtering (fail-safe).

    Behavior:
      - If context is set: auto-filters by organization_id
      - If context is not set: returns empty queryset (fail-safe)

    Reason: Prevents accidental data leaks when context is missing.
    """

    def get_queryset(self):
        org_id = get_current_organization()
        qs = super().get_queryset()

        if org_id:
            # Context set: filter automatically
            return qs.filter(organization_id=org_id)
        else:
            # Context NOT set: return empty queryset (explicit fail-safe)
            # This prevents accidental cross-tenant leaks
            return qs.none()
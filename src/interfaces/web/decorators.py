# src/interfaces/web/decorators.py

from functools import wraps
from django.shortcuts import redirect


def tenant_access_required(view_func):
    """
    Checks authentication + tenant ownership on every dashboard view.
    Superusers (is_superuser=True) may access any org slug freely.
    Regular users are restricted to their own organization.
    """
    @wraps(view_func)
    def wrapper(request, org_slug, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f'/auth/login/?next={request.path}')

        if not request.user.is_superuser:
            user_org = request.user.organization
            if not user_org or user_org.slug != org_slug:
                target = f'/dashboard/{user_org.slug}/' if user_org else '/auth/login/'
                return redirect(target)

        return view_func(request, org_slug, *args, **kwargs)

    return wrapper

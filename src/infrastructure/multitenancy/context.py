"""
Tenant context management using contextvars (async-safe, concurrent).

Replaces threading.local for modern async support.
"""
import contextvars
from typing import Optional
from uuid import UUID

_current_organization_context: contextvars.ContextVar[Optional[UUID]] = contextvars.ContextVar(
    'current_organization_id',
    default=None
)

def set_current_organization(org_id: Optional[UUID]) -> contextvars.Token:
    """Set organization context for current execution context.

    Args:
        org_id: Organization UUID or None to clear

    Returns:
        Token for restoring context (used by context manager)
    """
    if org_id and not isinstance(org_id, (str, UUID)):
        org_id = UUID(str(org_id))
    return _current_organization_context.set(org_id)

def get_current_organization() -> Optional[UUID]:
    """Get organization context.

    Returns:
        Organization UUID if set, None otherwise
    """
    return _current_organization_context.get()

def clear_current_organization() -> None:
    """Clear organization context (set to None)."""
    _current_organization_context.set(None)

def reset_context(token: contextvars.Token) -> None:
    """Reset context to previous state using token.

    Used by context managers to restore previous context.
    """
    _current_organization_context.reset(token)

class TenantContextManager:
    """Context manager for explicit tenant scoping.

    Usage:
        with TenantContextManager(org_uuid):
            # Code inside has org_uuid as context
            orders = Order.objects.all()  # Auto-filtered
    """

    def __init__(self, org_id: UUID):
        self.org_id = org_id
        self.token = None

    def __enter__(self):
        self.token = set_current_organization(self.org_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.token:
            reset_context(self.token)
        else:
            clear_current_organization()
        return False

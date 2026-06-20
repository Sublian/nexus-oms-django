"""Celery task utilities for tenant context management."""

from functools import wraps
from uuid import UUID
from celery import shared_task as celery_shared_task

from .multitenancy.context import set_current_organization, clear_current_organization


def tenant_task(organization_id_param: int = 0, **celery_kwargs):
    """Decorator for Celery tasks that require tenant context.

    Automatically manages organization_id context before and after task execution.

    Args:
        organization_id_param: Position of organization_id argument in task params
        **celery_kwargs: Arguments to pass to celery.shared_task (bind, name, max_retries, etc.)

    Usage:
        @tenant_task(organization_id_param=1)
        def my_task(self, entry_id, organization_id):
            # organization_id context is automatically set
            entry = MyModel.objects.get(id=entry_id)  # Uses context
            # ...

    Example:
        @tenant_task(organization_id_param=1, bind=True)
        def sync_invoice(self, entry_id, org_id):
            entry = InvoiceSyncQueue.objects.get(id=entry_id)
            return entry.id
    """

    def decorator(func):
        # Apply celery.shared_task
        celery_func = celery_shared_task(**celery_kwargs)(func)

        # Wrap with tenant context manager
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract organization_id from args (skip 'self' for bound tasks)
            # For bound tasks: args = (self, *task_args)
            # Position in task_args is organization_id_param
            try:
                task_args = args[1:] if celery_kwargs.get('bind', False) else args
                if organization_id_param < len(task_args):
                    org_id = task_args[organization_id_param]
                else:
                    org_id = kwargs.get('organization_id')

                if not org_id:
                    raise ValueError(
                        f"tenant_task requires organization_id "
                        f"(param position {organization_id_param} or kwarg)"
                    )

                # Ensure it's a UUID
                if org_id and not isinstance(org_id, UUID):
                    try:
                        org_id = UUID(str(org_id))
                    except (ValueError, TypeError) as e:
                        raise ValueError(f"Invalid organization_id: {org_id}") from e

                # Set context, run task, always clean up
                try:
                    set_current_organization(org_id)
                    return celery_func(*args, **kwargs)
                finally:
                    clear_current_organization()

            except Exception as e:
                # Log and re-raise
                import logging
                logger = logging.getLogger(__name__)
                logger.exception(f"Error in tenant_task wrapper: {e}")
                raise

        return wrapper

    return decorator

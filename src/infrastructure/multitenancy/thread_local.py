import threading

_thread_locals = threading.local()

def set_current_organization(org_id):
    setattr(_thread_locals, 'organization_id', org_id)

def get_current_organization():
    return getattr(_thread_locals, 'organization_id', None)

def clear_current_organization():
    if hasattr(_thread_locals, 'organization_id'):
        delattr(_thread_locals, 'organization_id')
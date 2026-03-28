# src/interfaces/web/context_processors.py

def tenant_context(request):
    """
    Toma la organización inyectada por el middleware y la pasa a los templates.
    """
    # Asumiendo que tu middleware ya inyecta la organización en el request
    return {
        'tenant': getattr(request, 'organization', None)
    }
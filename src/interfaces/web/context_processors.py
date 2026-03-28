# src/interfaces/web/context_processors.py

def tenant_context(request):
    """
    Hace que el objeto 'organization' esté disponible globalmente 
    en todos los templates HTML del proyecto.
    """
    # Asumiendo que tu middleware ya inyecta la organización en el request
    return {
        'tenant': getattr(request, 'organization', None)
    }
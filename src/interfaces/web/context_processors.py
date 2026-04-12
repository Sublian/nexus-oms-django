# src/interfaces/web/context_processors.py

from domain.services.finance_service import ExchangeService

def exchange_rate_context(request):
    # Solo ejecutamos esto si estamos en el dashboard (opcional, por performance)
    if not request.path.startswith('/dashboard/'):
        return {}
    
    return {
        'current_exchange': ExchangeService.get_current_rate()
    }

def tenant_context(request):
    """
    Toma la organización inyectada por el middleware y la pasa a los templates.
    """
    # Asumiendo que tu middleware ya inyecta la organización en el request
    return {
        'tenant': getattr(request, 'organization', None)
    }
    
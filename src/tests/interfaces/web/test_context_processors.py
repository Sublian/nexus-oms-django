import pytest
from django.test import RequestFactory
from src.interfaces.web.context_processors import exchange_rate_context

@pytest.mark.django_db
def test_exchange_rate_context_in_dashboard():
    factory = RequestFactory()
    # Simular petición al dashboard
    request = factory.get('/dashboard/mykonos-shop/orders/')
    
    context = exchange_rate_context(request)
    
    assert 'current_exchange' in context
    # Debería devolver un objeto ExchangeRate (o el fallback guardado)
    assert context['current_exchange'] is not None

def test_exchange_rate_context_outside_dashboard():
    factory = RequestFactory()
    # Petición fuera del dashboard (ej. login o home pública)
    request = factory.get('/login/')
    
    context = exchange_rate_context(request)
    
    # Debería devolver un dict vacío por optimización según tu lógica
    assert context == {}
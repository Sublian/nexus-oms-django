import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import patch
from src.domain.models.finance import ExchangeRate
from src.domain.services.finance_service import ExchangeService

@pytest.mark.django_db
class TestExchangeService:

    def test_get_rate_from_db_first(self):
        """
        Escenario 1: Si el dato ya existe en BD, NO debe llamar a la API.
        """
        today = date.today()
        ExchangeRate.objects.create(
            date=today,
            buy_price=Decimal("3.750"),
            sell_price=Decimal("3.780"),
            origin="test_db"
        )

        with patch('src.infrastructure.services.apimigo.APIMigoClient.get_exchange_rate') as mock_api:
            rate = ExchangeService.get_current_rate()
            
            assert rate.buy_price == Decimal("3.750")
            # Verificamos que NO se llamó a la API (ahorro de tiempo/costo)
            mock_api.assert_not_called()

    def test_get_rate_from_api_and_saves_it(self):
        """
        Escenario 2: Si no existe en BD, llama a API y guarda el resultado.
        """
        today = date.today()
        mock_response = {
            'success': True,
            'precio_compra': '3.700',
            'precio_venta': '3.740',
            'moneda': 'USD'
        }

        with patch('src.infrastructure.services.apimigo.APIMigoClient.get_exchange_rate', return_value=mock_response):
            # Aseguramos que la BD esté vacía para hoy
            ExchangeRate.objects.filter(date=today).delete()
            
            rate = ExchangeService.get_current_rate()
            
            assert rate.buy_price == Decimal("3.700")
            assert rate.origin == 'apimigo'
            # Verificar que se persistió
            assert ExchangeRate.objects.filter(date=today).exists()

    def test_fallback_when_api_fails(self):
        """
        Escenario 3: Si la API falla, el servicio debe manejar el fallback 
        definido en el cliente o servicio.
        """
        with patch('src.infrastructure.services.apimigo.APIMigoClient.get_exchange_rate') as mock_api:
            # Simulamos un fallo total de la API
            mock_api.return_value = {
                'success': False,
                'precio_compra': '3.75', 
                'precio_venta': '3.80'
            }
            
            rate = ExchangeService.get_current_rate()
            
            assert rate.origin == 'fallback'
            assert rate.buy_price == Decimal("3.75")
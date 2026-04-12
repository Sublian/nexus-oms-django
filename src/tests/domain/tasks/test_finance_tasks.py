import pytest
from unittest.mock import patch
from src.domain.tasks.finance_tasks import sync_daily_exchange_rate

@pytest.mark.django_db
def test_sync_daily_exchange_rate_task_calls_service():
    with patch('src.domain.services.finance_service.ExchangeService.get_current_rate') as mock_service:
        sync_daily_exchange_rate.delay() # Usamos delay para probar la firma de Celery
        # En los tests, shared_task se ejecuta síncronamente si eager está activo
        sync_daily_exchange_rate() 
        
        assert mock_service.called
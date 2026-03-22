import pytest
from src.domain.notifications.service import NotificationService

def test_notification_service_calls_correct_strategies(mocker):
    # Mock de las estrategias para no enviar correos reales
    mock_email = mocker.patch('src.infrastructure.notifications.strategies.EmailNotification.send')
    mock_telegram = mocker.patch('src.infrastructure.notifications.strategies.TelegramNotification.send')
    
    config = {
        'telegram_enabled': True,
        'whatsapp_enabled': False
    }
    
    NotificationService.notify_report_ready(config, "test@example.com", "Reporte Mensual")
    
    # Verificamos que se llamó al email (siempre) y a telegram (según config)
    assert mock_email.called
    assert mock_telegram.called
    # WhatsApp no debería llamarse
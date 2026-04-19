import pytest
from unittest.mock import patch
from src.domain.notifications.service import NotificationService
from src.domain.tasks.notification_tasks import alert_unusual_return_task
from src.domain.models.sales import Order, OrderReturn

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


@pytest.mark.django_db
def test_alert_unusual_return_task(organization, product):
    
    order = Order.objects.create(organization=organization, customer_name="Test")
    
    # 1. Crear el objeto cumpliendo con los campos NOT NULL
    ret = OrderReturn.objects.create(
        organization=organization,
        order=order,
        product=product,  # Campo obligatorio según el error
        quantity=1,       # Campo obligatorio según el error
        reason="Fraude detectado"
    )
    
    # 2. Configurar flags para cobertura de NotificationService
    organization.telegram_enabled = True
    organization.save()

    result = alert_unusual_return_task(ret.id)
    assert "Alerta enviada" in result

@pytest.mark.django_db
def test_alert_unusual_return_error():
    
    # Testeamos el 'except' pasando un ID que no existe (Línea 39-40)
    result = alert_unusual_return_task(9999)
    assert "Error" in result
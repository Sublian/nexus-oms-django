# Pruebas de Tareas de Celery (Mocks & Logic)

from datetime import date, timedelta
from django.utils import timezone

import pytest
from src.domain.tasks import generate_sales_report_task
from src.domain.models import SalesReport, Order

@pytest.mark.django_db
def test_generate_sales_report_task_creates_record(organization, product, mocker):
    # Mock de la caché para no depender de Redis en el test unitario
    mocker.patch('django.core.cache.cache.get', return_value=None)
    mocker.patch('django.core.cache.cache.set')

    # Ejecutamos la tarea de forma síncrona para el test (.apply() o directo)
    generate_sales_report_task(organization.id)
    
    # Verificamos que se creó el objeto en la DB
    assert SalesReport.objects.filter(organization=organization).exists()
    report = SalesReport.objects.first()
    assert report.organization == organization



def test_generate_sales_report_task_success(organization):
    # 1. Crear data para el reporte
    Order.objects.create(
        organization=organization, 
        customer_name="Luis Test", 
        total_amount=150
    )

    # 2. Pasar objetos date en lugar de strings
    end = timezone.now()
    start = end - timedelta(days=30)
    
    # 3. Ejecutar tarea
    result = generate_sales_report_task(organization.id, start, end)
    
    # 4. Validar resultado (ajustado a tu mensaje real)
    assert "generado" in result.lower()
# Pruebas de Tareas de Celery (Mocks & Logic)

import pytest
from src.domain.tasks import generate_sales_report_task
from src.domain.models import SalesReport

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
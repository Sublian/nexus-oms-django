# src/tests/domain/tasks/test_reporting_tasks.py
import pytest
from decimal import Decimal

from django.core.cache import cache

from src.domain.tasks.reporting_tasks import trigger_periodic_reports, generate_monthly_report_task, generate_order_pdf_task, monto_a_letras
from src.domain.models import Order, OrderItem

@pytest.mark.django_db
def test_monthly_report_with_cache(organization):
    # Primer ejecución: Genera y guarda en caché
    res1 = generate_monthly_report_task(organization.id, month=1, year=2026)
    assert "reporte" in res1.lower()
    
    # Segunda ejecución: Debe entrar al bloque de caché (Línea 95 aprox)
    res2 = generate_monthly_report_task(organization.id, month=1, year=2026)
    assert "CACHÉ" in res2


@pytest.mark.django_db
def test_order_pdf_generation_full_flow(organization, product):   

    # 1. Crear orden con monto específico para probar monto_a_letras
    order = Order.objects.create(organization=organization, customer_name="Test PDF", total_amount=Decimal('150.50'))
    OrderItem.objects.create(order=order, product=product, quantity=1, price_at_order=Decimal('150.50'), organization=organization)

    # 2. Probar función auxiliar de letras directamente
    letras = monto_a_letras(Decimal('150.50'))
    assert "CIENTO CINCUENTA" in letras
    assert "50/100" in letras

    # 3. Ejecutar la tarea del PDF (Líneas 166-200)
    # Usamos .run() o la llamamos directo para evitar que se vaya a Celery en el test
    result = generate_order_pdf_task(order.id)
    
    order.refresh_from_db()
    assert order.pdf_report.name is not None
    assert "PDF para Orden" in result


@pytest.mark.django_db
def test_trigger_periodic_reports(organization):
    # Esto ejecutará el .iterator() sobre todas las Orgs
    # No necesitamos verificar el envío de mail, solo que el loop corra
    result = trigger_periodic_reports(frequency='daily')
    assert result is None # O lo que retorne tu función        
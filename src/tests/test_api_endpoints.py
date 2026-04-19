# Pruebas de Integración de API (Client Tests)

# src/tests/test_api_endpoints.py
import pytest
from django.urls import reverse
from rest_framework import status
from src.domain.models import Order

@pytest.mark.django_db
class TestOrderAPI:
    def test_list_orders_only_returns_tenant_data(self, api_client, organization, org_factory):
        # Usamos la factory para evitar el error de IntegrityError
        other_org = org_factory("Competitor Corp")
        
        # Datos para el Tenant A
        Order.objects.create(organization=organization, customer_name="Cliente A")
        # Datos para el Tenant B
        Order.objects.create(organization=other_org, customer_name="Cliente B")

        url = reverse('order-list')
        
        # Ejecución con el Header del Tenant A
        response = api_client.get(url, HTTP_X_ORG_ID=str(organization.id))
        
        assert response.status_code == status.HTTP_200_OK
        # Solo debe ver 1 orden, la suya
        assert len(response.data) == 1
        assert response.data[0]['customer_name'] == "Cliente A"


    def test_trigger_report_endpoint(self, api_client, organization, mocker):
        """Sube cobertura en views.py disparando la acción trigger_report"""
        # Mock de la tarea de Celery
        mock_task = mocker.patch('src.domain.tasks.reporting_tasks.generate_sales_report_task.delay')
        # Simulamos que la tarea devuelve un ID ficticio
        mock_task.return_value.id = "fake-task-id"

        # El nombre correcto según tu router (report) y tu @action (trigger_report)
        url = reverse('report-trigger-report')
        
        # Enviamos datos para que el serializer sea válido (evita 400 Bad Request)
        data = {
            "start_date": "2026-01-01",
            "end_date": "2026-03-15"
        }

        response = api_client.post(url, data, HTTP_X_ORG_ID=str(organization.id))
        
        # Tu ViewSet devuelve 200 OK (según el decorador @extend_schema)
        # CAMBIO: Ahora esperamos 202 (Accepted) por ser proceso asíncrono
        assert response.status_code == 202
        assert response.data['task_id'] == "fake-task-id"
        assert "task_id" in response.data
        assert mock_task.called


        
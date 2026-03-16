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
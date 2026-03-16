# Pruebas de Integración de API (Client Tests)

import pytest
from django.urls import reverse
from rest_framework import status

@pytest.mark.django_db
class TestOrderAPI:
    
    def test_list_orders_only_returns_tenant_data(self, api_client, organization):
        # Creamos una segunda organización (la intrusa)
        from src.domain.models import Organization, Order
        other_org = Organization.objects.create(name="Competitor Org")
        
        # Orden de nuestra organización
        Order.objects.create(organization=organization, customer_name="Mi Cliente")
        # Orden de la otra organización
        Order.objects.create(organization=other_org, customer_name="Cliente Ajeno")

        url = reverse('order-list') # Ajusta según tu router
        
        # Simulamos el header que usa tu Middleware
        response = api_client.get(url, HTTP_X_ORG_ID=str(organization.id))
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['customer_name'] == "Mi Cliente"
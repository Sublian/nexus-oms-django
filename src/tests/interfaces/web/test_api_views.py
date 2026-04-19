import pytest
from django.urls import reverse
from rest_framework import status
from src.domain.models import Product, Order, Organization
from src.infrastructure.multitenancy.middleware import set_current_organization

@pytest.mark.django_db
class TestOrderAPI:
    def test_create_order_isolation(self, api_client, organization, product):
        # 1. Creamos una SEGUNDA organización real para no violar la integridad
        other_org = Organization.objects.create(name="Otra Org", slug="otra")
        
        other_org_product = Product.objects.create(
            name="Producto Ajeno",
            sku="AJENO001",
            price=100.00,
            organization=other_org  # Usamos una organización que SÍ existe
        )
        
        # 2. Usamos el namespace correcto. Según tu urls.py es 'web'
        # Si es una API con Router de Django Rest Framework, verifica dónde se incluye
        # url = reverse('web:order-list', kwargs={'org_slug': other_org.slug})
        url = reverse('order-list')
        
        data = {
            "product_id": other_org_product.id,
            "quantity": 1
        }
        
        response = api_client.post(url, data)
        # Debería fallar porque el producto no pertenece a la organización del usuario
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_order_return_api_validation(self, api_client, organization, product):
        """Prueba el flujo de error en la API de devoluciones."""
        # 1. Forzamos manualmente que el hilo actual conozca la organización
        set_current_organization(organization.id)
        
        order = Order.objects.create(organization=organization, customer_name="Test")
        # url = reverse('web:order-list', kwargs={'org_slug': organization.slug})
        url = reverse('order_returns-list')
        # Intentamos devolver cantidad negativa
        data = {
            "order": order.id,
            "product": product.id,
            "quantity": -5,
            "reason": "DEFECTIVE"
        }
        
        response = api_client.post(url, data, format='json', HTTP_X_TENANT_ID=str(organization.id))
        
        # 3. Limpiamos el thread después del test (buena práctica)
        set_current_organization(None)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
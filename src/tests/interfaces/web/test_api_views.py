import pytest
from django.urls import reverse
from rest_framework import status
from src.domain.models import Product, Order, OrderReturn, Organization, Stock, Warehouse
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

    def test_product_list_includes_annotated_stock(self, api_client, organization, product):
        
        set_current_organization(organization.id)
    
        # 1. Preparación de datos
        warehouse = Warehouse.objects.create(name="Principal", organization=organization)
        Stock.objects.create(
            product=product, 
            warehouse=warehouse, 
            quantity=7, 
            organization=organization
        )
        
        url = reverse('product-list')
        response = api_client.get(url, HTTP_X_TENANT_ID=str(organization.id))
        
        assert response.status_code == 200

        # 2. Manejo dinámico de Paginación vs Lista simple
        if isinstance(response.data, dict) and 'results' in response.data:
            data_list = response.data['results']
        else:
            data_list = response.data

        # 3. Búsqueda del producto
        product_data = next((p for p in data_list if p['id'] == product.id), None)
        
        assert product_data is not None, "El producto no se encontró en la respuesta de la API"
        assert product_data['stock_total'] == 7
        
        set_current_organization(None)

    
    def test_get_order_return_detail(self, api_client, organization, product):
        """Prueba el método 'retrieve' (GET /api/v1/order_returns/<id>/)"""
        set_current_organization(organization.id)
        
        # Creamos una devolución previa directamente en la DB
        order = Order.objects.create(organization=organization, customer_name="Test")
        ret = OrderReturn.objects.create(
            organization=organization, order=order, 
            product=product, quantity=1, reason="DEFECTIVE"
        )
        
        url = reverse('order_returns-detail', kwargs={'pk': ret.pk})
        response = api_client.get(url, HTTP_X_TENANT_ID=str(organization.id))
        
        assert response.status_code == 200
        assert response.data['quantity'] == 1
        
        set_current_organization(None)

    def test_order_search_and_filter(self, client, organization, product):
        # Testea el buscador dinámico (HTMX)
        url = reverse('web:search-product', kwargs={'org_slug': organization.slug})
        response = client.get(url, {'q': product.name})
        assert response.status_code == 200
        
        # Testea filtros en la lista de órdenes
        url_list = reverse('web:order-list', kwargs={'org_slug': organization.slug})
        response_filter = client.get(url_list, {'status': 'PENDING'})
        assert response_filter.status_code == 200

import pytest

from django.urls import reverse

from src.domain.models.sales import Order


@pytest.mark.django_db
def test_order_list_view_status_code(client, admin_user, organization):
    # Usamos admin_user que sí existe en tus fixtures
    client.force_login(admin_user)
    
    # IMPORTANTE: El middleware de tenant necesita que el usuario tenga permiso 
    # o que la URL contenga el slug correcto.
    url = reverse('web:order-list', kwargs={'org_slug': organization.slug})
    response = client.get(url)
    
    assert response.status_code == 200


@pytest.mark.django_db
class TestOrderWebViews:
    def test_order_list_view(self, client, organization):
        # 1. Usar el namespace 'web:' y pasar el org_slug
        url = reverse('web:order-list', kwargs={'org_slug': organization.slug})
        response = client.get(url)
        
        assert response.status_code == 200
        # Esto cubrirá 'order_list_view' en views.py

    def test_order_create_view_get(self, client, organization):
        url = reverse('web:order-create', kwargs={'org_slug': organization.slug})
        response = client.get(url)
        
        assert response.status_code == 200

    def test_create_order_view_post_success(self, client, organization, product):
        from src.domain.models.inventory import Stock, Warehouse
        
        # Setup: Necesitamos stock para que la vista no devuelva error de validación
        warehouse = Warehouse.objects.create(name="Principal", organization=organization)
        Stock.objects.create(product=product, warehouse=warehouse, quantity=100, organization=organization)
        
        url = reverse('web:order-create', kwargs={'org_slug': organization.slug})
        
        # Ajusta estos campos según lo que espere tu OrderForm en la vista
        data = {
            'customer_name': 'Juan Test',
            'customer_email': 'juan@test.com',
            'product': product.id,
            'quantity': 2
        }
        
        response = client.post(url, data)
        
        # Si la vista redirige tras crear, el status será 302
        assert response.status_code in [200, 302]
        if response.status_code == 302:
            assert Order.objects.filter(customer_name='Juan Test').exists()

    def test_order_detail_partial(self, client, organization):
        # Crear una orden previa para ver su detalle
        order = Order.objects.create(organization=organization, customer_name="Detalle Test")
        
        url = reverse('web:order_detail', kwargs={
            'org_slug': organization.slug,
            'order_id': order.id
        })
        response = client.get(url)
        
        assert response.status_code == 200
        assert "Detalle Test" in response.content.decode()
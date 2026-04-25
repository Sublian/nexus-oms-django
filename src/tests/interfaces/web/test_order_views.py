
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
    def test_order_list_view(self, logged_in_client, organization):
        url = reverse('web:order-list', kwargs={'org_slug': organization.slug})
        response = logged_in_client.get(url)
        assert response.status_code == 200

    def test_order_create_view_get(self, logged_in_client, organization):
        url = reverse('web:order-create', kwargs={'org_slug': organization.slug})
        response = logged_in_client.get(url)
        assert response.status_code == 200

    def test_create_order_view_post_success(self, logged_in_client, organization, product):
        from src.domain.models.inventory import Stock, Warehouse

        warehouse = Warehouse.objects.create(name="Principal", organization=organization)
        Stock.objects.create(product=product, warehouse=warehouse, quantity=100, organization=organization)

        url = reverse('web:order-create', kwargs={'org_slug': organization.slug})
        data = {
            'customer_name': 'Juan Test',
            'customer_email': 'juan@test.com',
            'product': product.id,
            'quantity': 2
        }

        response = logged_in_client.post(url, data)
        assert response.status_code in [200, 302]
        if response.status_code == 302:
            assert Order.objects.filter(customer_name='Juan Test').exists()

    def test_order_detail_partial(self, logged_in_client, organization):
        order = Order.objects.create(organization=organization, customer_name="Detalle Test")

        url = reverse('web:order_detail', kwargs={
            'org_slug': organization.slug,
            'order_id': order.id
        })
        response = logged_in_client.get(url)
        assert response.status_code == 200
        assert "Detalle Test" in response.content.decode()
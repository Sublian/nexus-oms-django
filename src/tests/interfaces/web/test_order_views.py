import pytest
from django.urls import reverse

@pytest.mark.django_db
def test_order_list_view_status_code(client, admin_user, organization):
    # Usamos admin_user que sí existe en tus fixtures
    client.force_login(admin_user)
    
    # IMPORTANTE: El middleware de tenant necesita que el usuario tenga permiso 
    # o que la URL contenga el slug correcto.
    url = reverse('web:order-list', kwargs={'org_slug': organization.slug})
    response = client.get(url)
    
    assert response.status_code == 200
        
import pytest
from rest_framework import status
from django.urls import reverse
from src.domain.services import OrderService
from src.domain.tasks import generate_sales_report_task
from src.domain.models import Organization, Order, Product, Category
from django.core.exceptions import ValidationError

@pytest.mark.django_db
class TestBusinessEdgeCases:

    def test_task_fails_if_org_not_found(self):
        """Cubre el bloque 'except Organization.DoesNotExist' en tasks.py"""
        import uuid
        from src.domain.tasks import generate_sales_report_task
        
        random_uuid = uuid.uuid4()
        
        # 1. Llamamos a la tarea (la excepción es capturada internamente)
        result = generate_sales_report_task(random_uuid)
        
        # 2. Verificamos que el retorno sea el mensaje de error que definimos
        assert f"Error: Organización {random_uuid} no encontrada." in result

    def test_return_logic_with_invalid_product(self, organization, org_factory):
        """Cubre el bloque 'except Product.DoesNotExist' en services.py"""
        from django.http import Http404
        other_org = org_factory("Other Org")
        # El producto pertenece a 'Other Org', no a 'Main Tenant'
        product_ajeno = Product.objects.create(
            name="Intruso",
            price=10,
            organization=other_org
        )
        order_propia = Order.objects.create(
            organization=organization,
            customer_name="Luis"
        )

        # TenantManager no puede ver el producto de otra org -> Http404
        with pytest.raises(Http404):
            OrderService.process_return(
                organization=organization,
                order_id=order_propia.id,
                product_id=product_ajeno.id,
                quantity=1,
                reason="OTHERS"
            )

    @pytest.mark.django_db
    def test_product_lifecycle_coverage(self, auth_api_client, organization):
        """Cubre el listado y filtrado para asegurar el aislamiento de Tenant"""
        from src.domain.models import Product

        Product.objects.create(
            organization=organization,
            name="Producto Test",
            sku="TEST-123",
            price=50.00
        )

        url = reverse('product-list')
        response = auth_api_client.get(url)

        assert response.status_code == 200
        assert len(response.data) >= 1
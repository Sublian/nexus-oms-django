import pytest
from src.domain.services import OrderService
from src.domain.tasks import generate_sales_report_task
from src.domain.models import Organization, Order, Product
from django.core.exceptions import ValidationError

@pytest.mark.django_db
class TestBusinessEdgeCases:

    def test_task_fails_if_org_not_found(self):
        """Cubre el bloque 'except Organization.DoesNotExist' en tasks.py"""
        import uuid
        # Ahora sí, atrapamos la excepción específica que lanza Django
        with pytest.raises(Organization.DoesNotExist):
            generate_sales_report_task(uuid.uuid4())

    def test_return_logic_with_invalid_product(self, organization, org_factory):
        """Cubre el bloque 'except Product.DoesNotExist' en services.py"""
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
        
        # El servicio lanza ValueError cuando el producto no es de la misma Org
        with pytest.raises(ValueError) as excinfo:
            OrderService.process_return(
                organization=organization,
                order_id=order_propia.id,
                product_id=product_ajeno.id,
                quantity=1,
                reason="OTHERS"
            )
        assert "no pertenece a esta organización" in str(excinfo.value)
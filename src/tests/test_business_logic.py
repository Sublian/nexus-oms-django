import pytest
from src.domain.services import OrderService
from src.domain.tasks import generate_sales_report_task
from django.core.exceptions import ValidationError

@pytest.mark.django_db
class TestBusinessEdgeCases:

    def test_task_fails_if_org_not_found(self, mocker):
        """Cubre líneas missing en tasks.py (error handling)"""
        import uuid
        # Intentamos generar reporte para una Org que no existe
        result = generate_sales_report_task(uuid.uuid4())
        assert "not found" in str(result).lower()

    def test_return_logic_with_invalid_product(self, organization, org_factory):
        """Sube cobertura en services.py (líneas 39-82)"""
        from src.domain.models import Order, Product
        
        other_org = org_factory("Other")
        product_ajeno = Product.objects.create(name="Intruso", price=10, organization=other_org)
        order_propia = Order.objects.create(organization=organization, customer_name="Luis")
        
        # Intentar devolver un producto que no pertenece a la organización de la orden
        with pytest.raises(ValidationError):
            OrderService.process_return(
                organization=organization,
                order_id=order_propia.id,
                product_id=product_ajeno.id,
                quantity=1,
                reason="OTHERS"
            )
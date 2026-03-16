import pytest
from django.core.exceptions import ValidationError
from src.domain.services import OrderService
from src.domain.models import Order, OrderItem

@pytest.mark.django_db
class TestOrderReturn:
    
    def test_return_fails_if_quantity_is_zero(self, organization, product):
        # Creamos una orden mínima
        order = Order.objects.create(organization=organization, customer_name="Luis")
        
        with pytest.raises(ValidationError) as excinfo:
            OrderService.process_return(
                organization=organization,
                order_id=order.id,
                product_id=product.id,
                quantity=0, # CASO CRÍTICO
                reason="OTHERS"
            )
        assert "mayor a cero" in str(excinfo.value)

    def test_return_fails_if_exceeds_original_quantity(self, organization, product):
        order = Order.objects.create(organization=organization, customer_name="Luis")
        OrderItem.objects.create(order=order, product=product, quantity=5)
        
        with pytest.raises(ValidationError) as excinfo:
            OrderService.process_return(
                organization=organization,
                order_id=order.id,
                product_id=product.id,
                quantity=10, # EXCESO
                reason="OTHERS"
            )
        assert "Operación no permitida" in str(excinfo.value)

    def test_return_success_updates_stock(self, organization, product, mocker):
        # Mockeamos la tarea de Celery para que no se ejecute realmente en el test unitario
        mock_task = mocker.patch('src.domain.tasks.alert_unusual_return_task.delay')
        
        order = Order.objects.create(organization=organization, customer_name="Luis")
        OrderItem.objects.create(order=order, product=product, quantity=5)
        
        # Ejecutamos el servicio
        result = OrderService.process_return(
            organization=organization,
            order_id=order.id,
            product_id=product.id,
            quantity=2,
            reason="OTHERS"
        )
        
        assert result.quantity == 2
        # Verificamos que el Mock de la tarea fue llamado
        mock_task.assert_called_once_with(result.id)
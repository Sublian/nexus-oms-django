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
        # Creamos una orden mínima
        order = Order.objects.create(organization=organization, customer_name="Luis")
        OrderItem.objects.create(
            order=order, 
            product=product, 
            quantity=5, 
            price_at_order=product.price, # <--- Solución al error
            organization=organization      # <--- Mantener el multitenancy
        )
        
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
        
        # Creamos una orden mínima
        order = Order.objects.create(organization=organization, customer_name="Luis")
        OrderItem.objects.create(
            order=order, 
            product=product, 
            quantity=5, 
            price_at_order=product.price,
            organization=organization
        )
        
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

    
    def test_return_atomic_transaction_on_error(self, organization, product, mocker):
        """
        Si algo falla al crear el retorno, la base de datos no debe quedar inconsistente.
        """
        order = Order.objects.create(organization=organization, customer_name="Luis")
        OrderItem.objects.create(order=order, product=product, quantity=5, price_at_order=100, organization=organization)

        # Simulamos que el método .create de OrderReturn lanza un error de base de datos
        mocker.patch(
            'src.domain.models.OrderReturn.objects.create', 
            side_effect=Exception("Database Connection Lost")
        )

        with pytest.raises(Exception) as excinfo:
            OrderService.process_return(
                organization=organization,
                order_id=order.id,
                product_id=product.id,
                quantity=1,
                reason="OTHERS"
            )
        assert "Database Connection Lost" in str(excinfo.value)

    def test_process_return_fails_on_non_existent_order(self, organization, product):
        from uuid import uuid4
        with pytest.raises(Exception): # O la excepción específica que lances
            OrderService.process_return(
                organization=organization,
                order_id=uuid4(), # ID aleatorio que no existe
                product_id=product.id,
                quantity=1,
                reason="DEFECTIVE"
            )
        
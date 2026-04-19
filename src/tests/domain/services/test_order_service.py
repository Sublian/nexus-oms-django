from datetime import date
from decimal import Decimal
from datetime import timedelta
import pytest

from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction
from src.domain.services import OrderService, get_net_margin_report
from src.domain.models import Order, OrderItem, Stock,  Payment, PurchaseOrder, PurchaseOrderItem, Stock, Warehouse, Supplier

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
        # CAMBIO: Actualizamos el string esperado para que coincida con el servicio
        # assert "Máximo disponible para devolver" in str(excinfo.value)
        assert "La cantidad excede el disponible para devolución" in str(excinfo.value)


    @pytest.mark.django_db(transaction=True)
    def test_return_success_updates_stock(self, organization, product, mocker):
        # Mock de la tarea
        mock_task = mocker.patch('src.domain.tasks.notification_tasks.alert_unusual_return_task.delay')
        
        # 🛡️ Envolvemos la creación en atomic para satisfacer el select_for_update de la señal
        with transaction.atomic():
            order = Order.objects.create(organization=organization, customer_name="Luis")
            OrderItem.objects.create(
                order=order, 
                product=product, 
                quantity=5,
                price_at_order=product.price, 
                organization=organization
            )

        # Ejecutamos el servicio (que ya tiene su propio @transaction.atomic)
        result = OrderService.process_return(
            organization=organization,
            order_id=order.id,
            product_id=product.id,
            quantity=2,
            reason="OTHERS"
        )

        assert result.quantity == 2
        
        # Verificamos la llamada
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
        

@pytest.mark.django_db
class TestOrderServiceReturn:
    def test_process_return_success(self, organization, product):
        # 1. Preparación: Crear una orden previa
        
        order = Order.objects.create(organization=organization, customer_name="Cliente Éxito")
        
        # 2. ¡CRUCIAL!: Debemos agregar el producto a la orden para que la validación pase
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=5,
            price_at_order=product.price,
            organization=organization
        )
        
        # 3. Ahora el servicio sí encontrará el producto en la orden
        order_return = OrderService.process_return(
            organization=organization,
            order_id=order.id,
            product_id=product.id,
            quantity=2,
            reason="DEFECTIVE",
            notes="Pantalla rayada"
        )
        
        assert order_return.id is not None
        assert order_return.quantity == 2

    def test_process_return_invalid_order(self, organization, product):
        """Prueba que falla si la orden no existe."""
        with pytest.raises(Exception): # O la excepción específica que lances
            OrderService.process_return(organization, 9999, product.id, 1, "REASON")

    def test_process_return_exceeds_quantity(self, organization, product):
        """
        Si tienes lógica que impide devolver más de lo comprado, 
        este test cubrirá esas líneas.
        """
        order = Order.objects.create(organization=organization, customer_name="Test")
        OrderItem.objects.create(
            order=order, product=product, quantity=5, 
            price_at_order=100, organization=organization
        )
        
        # Intentar devolver 10 cuando solo se compraron 5
        with pytest.raises(ValidationError):
            OrderService.process_return(organization, order.id, product.id, 10, "DEFECTIVE")
    

    @pytest.mark.django_db
    def test_get_net_margin_report_logic(self, organization, product): # <--- Agregar self

        # 1. SOLUCIÓN AL ERROR DE INTEGRIDAD: Crear el Supplier real
        supplier = Supplier.objects.create(name="Proveedor Test", organization=organization)
        warehouse = Warehouse.objects.create(name="Principal", organization=organization)
        
        # 2. SOLUCIÓN AL ASSERTION ERROR: Usar fechas con zona horaria
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        # Crear historial de compra (COGS)
        po = PurchaseOrder.objects.create(
            organization=organization, 
            status='RECEIVED', 
            supplier=supplier, # Usamos el objeto creado
            warehouse=warehouse
        )
        PurchaseOrderItem.objects.create(
            purchase_order=po, product=product, quantity=10, 
            unit_cost=Decimal('50.00'), organization=organization
        )
        
        # Crear orden y pago
        order = Order.objects.create(organization=organization, customer_name="Test")
        OrderItem.objects.create(
            order=order, product=product, quantity=2, 
            price_at_order=Decimal('100.00'), organization=organization
        )
        
        # Forzamos la fecha del pago para que entre en el rango del reporte
        Payment.objects.create(
            organization=organization, 
            order=order, 
            amount=Decimal('200.00'), 
            fee_amount=Decimal('5.00'),
            payment_date=timezone.now() 
        )
        
        # 3. Ejecutar reporte con el rango correcto
        report = get_net_margin_report(organization, today_start, today_end)
        
        assert report['revenue'] == Decimal('200.00')
        assert report['cogs'] == Decimal('100.00') 
        assert report['net_profit'] == Decimal('95.00')

    def test_create_order_success(self, organization, product): # <--- Agregar self
        from src.domain.models.inventory import Stock, Warehouse
        
        w = Warehouse.objects.create(name="Web", organization=organization)
        Stock.objects.create(product=product, warehouse=w, quantity=10, organization=organization)
        
        customer_data = {'name': 'Juan Perez', 'email': 'juan@example.com'}
        items_data = [{'product': product, 'quantity': 2}]
        
        order = OrderService.create_order(organization, customer_data, items_data)
        
        assert order.status == 'PENDING'
        assert order.subtotal == product.price * 2

    def test_create_order_insufficient_stock(self, organization, product): # <--- Agregar self
        customer_data = {'name': 'Fail', 'email': 'fail@test.com'}
        items_data = [{'product': product, 'quantity': 1000}]
        
        with pytest.raises(ValueError, match="Stock insuficiente"):
            OrderService.create_order(organization, customer_data, items_data)


    def test_order_return_logic(self, organization, product):
        
        # 1. Crear orden completada
        order = Order.objects.create(organization=organization, status='COMPLETED')
        item = OrderItem.objects.create(order=order, product=product, quantity=5, price_at_order=100, organization=organization)
        
        service = OrderService()
        # Probemos pasando los argumentos como espera la mayoría de tus servicios:
        # (Ajusta si tu método se llama distinto, ej: create_return)
        result = service.process_return(
            organization=organization,
            order_id=order.id, 
            product_id=product.id, 
            quantity=2, 
            reason="Defectuoso",
            notes="TEST"
        )
        
        assert result is not None
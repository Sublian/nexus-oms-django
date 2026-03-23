import pytest
from decimal import Decimal
from src.domain.models import (
    Warehouse, Stock, Order, OrderItem, 
    StockMovement, OrderReturn, Payment,
    Supplier, PurchaseOrder, PurchaseOrderItem
)

@pytest.fixture
def warehouse(db, organization):
    return Warehouse.objects.create(name="Almacén Central", organization=organization)

@pytest.fixture
def supplier(db, organization):
    return Supplier.objects.create(name="Proveedor Nike", organization=organization)

@pytest.mark.django_db
class TestInventoryLogic:
    """Pruebas para el Kárdex y Movimientos de Stock."""

    def test_stock_decreases_on_sale_signal(self, organization, product, warehouse):
        # 1. Setup: Iniciamos stock en 10
        stock = Stock.objects.create(
            product=product, warehouse=warehouse, quantity=10, organization=organization
        )

        # 2. Action: Creamos una orden de venta por 2 unidades
        order = Order.objects.create(
            organization=organization, customer_name="Luis", customer_email="luis@test.com"
        )
        OrderItem.objects.create(
            order=order, product=product, quantity=2, price_at_order=product.price, 
            organization=organization
        )

        # 3. Assert: El stock debe ser 8 y debe existir un movimiento de salida
        stock.refresh_from_db()
        assert stock.quantity == 8
        
        movement = StockMovement.objects.get(stock=stock, order=order)
        assert movement.movement_type == StockMovement.MovementType.OUTPUT
        assert movement.quantity == 2

    def test_stock_reentry_on_return(self, organization, product, warehouse):
        # Setup: Stock en 5 y venta previa
        stock = Stock.objects.create(
            product=product, warehouse=warehouse, quantity=5, organization=organization
        )
        order = Order.objects.create(organization=organization, customer_name="Dev")

        # Action: Devolución de 2 unidades que vuelven a estantería
        OrderReturn.objects.create(
            order=order, product=product, quantity=2, 
            reason=OrderReturn.Reason.MISTAKE, reentered_to_stock=True,
            organization=organization
        )

        # Assert: Stock debe subir a 7
        stock.refresh_from_db()
        assert stock.quantity == 7

@pytest.mark.django_db
class TestFinancialLogic:
    """Pruebas para Pagos y Compras."""

    def test_purchase_order_increases_stock(self, organization, product, warehouse, supplier):
        # 1. Creamos OC PENDIENTE
        po = PurchaseOrder.objects.create(
            supplier=supplier, 
            warehouse=warehouse, 
            organization=organization, # ✅ Tenía Org
            status=PurchaseOrder.POStatus.PENDING
        )
        
        # EL FIX ESTÁ AQUÍ: Agregamos organization al Item
        PurchaseOrderItem.objects.create(
            purchase_order=po, 
            product=product, 
            quantity=50, 
            unit_cost=Decimal('500.00'),
            organization=organization  # 👈 ESTO FALTABA
        )

        # El stock no debe existir/subir aún porque está PENDING
        assert Stock.objects.filter(product=product).count() == 0

        # 2. Cambiamos a RECEIVED (esto dispara la signal)
        po.status = PurchaseOrder.POStatus.RECEIVED
        po.save()

        # Assert: Stock debe existir con 50 y haber un INPUT en Kárdex
        stock = Stock.objects.get(product=product, organization=organization)
        assert stock.quantity == 50
        
        # Validar que el movimiento de Kárdex también tenga la Org correcta
        movement = StockMovement.objects.get(stock=stock, movement_type="INPUT")
        assert movement.quantity == 50
        assert movement.organization == organization
    
    def test_payment_fee_calculation(self, organization, product):
        order = Order.objects.create(organization=organization, total_amount=100)
        payment = Payment.objects.create(
            order=order, organization=organization, method="CARD", 
            amount=100, fee_amount=Decimal('3.50')
        )
        
        assert payment.net_amount == Decimal('96.50')
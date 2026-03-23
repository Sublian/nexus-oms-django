import pytest
from decimal import Decimal
from src.domain.services.finance_service import get_net_margin_report # Ajustado a nueva ruta

@pytest.mark.django_db
def test_net_margin_calculation_accuracy(organization, product, warehouse, supplier):
    # 1. Simulamos una COMPRA (Costo)
    # Compramos 10 unidades a 50.00 cada una
    from src.domain.models import PurchaseOrder, PurchaseOrderItem
    po = PurchaseOrder.objects.create(organization=organization, supplier=supplier, warehouse=warehouse, status='RECEIVED')
    PurchaseOrderItem.objects.create(organization=organization, purchase_order=po, product=product, quantity=10, unit_cost=Decimal('50.00'))

    # 2. Simulamos una VENTA (Ingreso)
    # Vendemos 2 unidades a 100.00 cada una
    from src.domain.services.order_service import OrderService
    customer = {'name': 'Juan', 'email': 'juan@test.com'}
    items = [{'product': product, 'quantity': 2}]
    order = OrderService.create_order(organization, customer, items) # Precio venta = 100 (del producto)

    # 3. Agregamos un PAGO con COMISIÓN
    from src.domain.models import Payment
    Payment.objects.create(organization=organization, order=order, amount=Decimal('200.00'), fee_amount=Decimal('10.00'), status='PAID')

    # 4. EJECUTAMOS EL REPORTE
    from django.utils import timezone
    now = timezone.now()
    report = get_net_margin_report(organization, now - timezone.timedelta(days=1), now + timezone.timedelta(days=1))

    # VALIDACIONES:
    # Revenue: 200.00
    # COGS: 2 unidades * 50.00 = 100.00
    # Fees: 10.00
    # Net Profit: 200 - 100 - 10 = 90.00
    assert report['revenue'] == Decimal('200.00')
    assert report['cogs'] == Decimal('100.00')
    assert report['net_profit'] == Decimal('90.00')
    assert report['margin_percentage'] == 45.0
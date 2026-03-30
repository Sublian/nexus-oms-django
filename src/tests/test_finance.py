import pytest
# from decimal import Decimal
# from src.domain.services.finance_service import get_net_margin_report # Ajustado a nueva ruta

@pytest.mark.django_db
def test_net_margin_calculation_accuracy(organization, product, warehouse, supplier):
    from decimal import Decimal
    from src.domain.models import Stock, TaxConfiguration, Payment, PurchaseOrder, PurchaseOrderItem
    from src.domain.services.order_service import OrderService
    from django.utils import timezone

    # --- PASO 0: Configuración de Impuestos (Indispensable ahora) ---
    # Creamos el impuesto por defecto para que los cálculos de la Orden funcionen
    TaxConfiguration.objects.get_or_create(
        organization=organization,
        name="IGV Test",
        rate=Decimal('18.00'),
        is_default=True
    )

    # --- PASO 1: Inyectar Stock ---
    Stock.objects.update_or_create(
        product=product, 
        organization=organization, 
        warehouse=warehouse,
        defaults={'quantity': 100} 
    )

    # --- PASO 2: Simular COMPRA (Costo) ---
    # 10 unidades a 50.00 c/u = $500 de inversión total
    po = PurchaseOrder.objects.create(
        organization=organization, 
        supplier=supplier, 
        warehouse=warehouse, 
        status='RECEIVED'
    )
    PurchaseOrderItem.objects.create(
        organization=organization, 
        purchase_order=po, 
        product=product, 
        quantity=10, 
        unit_cost=Decimal('50.00')
    )

    # --- PASO 3: Simular VENTA (Ingreso) ---
    # El producto tiene un precio (ej. 100.00). Vendemos 2 unidades.
    # IMPORTANTE: OrderService.create_order ya no debe intentar setear .subtotal manualmente
    customer = {'name': 'Juan', 'email': 'juan@test.com'}
    items = [{'product': product, 'quantity': 2}]
    
    # El Service creará la orden y los OrderItems. 
    # Las @properties del modelo Order calcularán el subtotal automáticamente.
    order = OrderService.create_order(organization, customer, items)

    # --- PASO 4: Registrar PAGO con COMISIÓN ---
    # Supongamos que el total de la orden fue 200.00
    Payment.objects.create(
        organization=organization, 
        order=order, 
        amount=Decimal('200.00'), 
        fee_amount=Decimal('10.00'),
        method='CARD',
        payment_date=timezone.now()
    )

    # --- PASO 5: EJECUTAR REPORTE ---
    now = timezone.now()
    # Asegúrate de importar tu función de reporte aquí
    from src.domain.services.finance_service import get_net_margin_report 
    
    report = get_net_margin_report(
        organization, 
        now - timezone.timedelta(days=1), 
        now + timezone.timedelta(days=1)
    )

    # --- VALIDACIONES ---
    # Revenue (Venta Bruta): 200.00
    # COGS (Costo de lo vendido): 2 unidades * 50.00 = 100.00
    # Fees (Comisiones): 10.00
    # Net Profit: 200 (Ingreso) - 100 (Costo) - 10 (Comisión) = 90.00
    
    assert report['revenue'] == Decimal('200.00')
    assert report['cogs'] == Decimal('100.00')
    assert report['net_profit'] == Decimal('90.00')
    
    # Margen = (90 / 200) * 100 = 45%
    assert float(report['margin_percentage']) == 45.0

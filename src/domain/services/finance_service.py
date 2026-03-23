from decimal import Decimal

from django.db.models import Sum
from django.db import transaction
from django.core.exceptions import ValidationError

from ..models import Payment, OrderItem, OrderReturn, PurchaseOrderItem


def calculate_expected_cash(organization, start_date, end_date):
    # 1. Sumar todos los pagos recibidos
    total_payments = Payment.objects.filter(
        organization=organization,
        payment_date__range=(start_date, end_date)
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # 2. Restar las devoluciones que implicaron reembolso
    total_refunds = OrderReturn.objects.filter(
        organization=organization,
        created_at__range=(start_date, end_date)
    ).aggregate(total=Sum('refund_amount'))['total'] or 0
    
    return total_payments - total_refunds

def get_net_margin_report(organization, start_date, end_date):
    # 1. Ingresos Totales (Ventas Pagadas)
    revenue = Payment.objects.filter(
        organization=organization,
        payment_date__range=(start_date, end_date)
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # 2. Comisiones de Pasarela (Gasto)
    fees = Payment.objects.filter(
        organization=organization,
        payment_date__range=(start_date, end_date)
    ).aggregate(total=Sum('fee_amount'))['total'] or Decimal('0.00')

    # 3. Costo de Mercancía Vendida (COGS)
    total_cost = Decimal('0.00')
    items_sold = OrderItem.objects.filter(
        organization=organization,
        order__created_at__range=(start_date, end_date)
    )

    for item in items_sold:
        # Buscamos el último costo de compra para este producto
        last_purchase = PurchaseOrderItem.objects.filter(
            product=item.product,
            purchase_order__status='RECEIVED'
        ).order_by('-purchase_order__created_at').first()
        
        cost_unit = last_purchase.unit_cost if last_purchase else item.price_at_order * Decimal('0.5')
        total_cost += (cost_unit * item.quantity)

    # 4. Devoluciones (Restan al ingreso)
    refunds = OrderReturn.objects.filter(
        organization=organization,
        created_at__range=(start_date, end_date)
    ).aggregate(total=Sum('refund_amount'))['total'] or Decimal('0.00')

    net_profit = revenue - total_cost - fees - refunds
    
    return {
        "revenue": revenue,
        "cogs": total_cost,
        "fees": fees,
        "refunds": refunds,
        "net_profit": net_profit,
        "margin_percentage": (net_profit / revenue * 100) if revenue > 0 else 0
    }



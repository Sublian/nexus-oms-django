from django.utils import timezone
from decimal import Decimal
from datetime import date

from django.db.models import Sum
from django.db import transaction
from django.core.exceptions import ValidationError

from ..models import Payment, OrderItem, OrderReturn, PurchaseOrderItem, ExchangeRate
from ...infrastructure.services.apimigo import APIMigoClient


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
    # 1. Ingresos y Comisiones (Consolidado en una sola consulta)
    payments_data = Payment.objects.filter(
        organization=organization,
        payment_date__range=(start_date, end_date)
    ).aggregate(
        total_revenue=Sum('amount'),
        total_fees=Sum('fee_amount')
    )
    
    revenue = payments_data['total_revenue'] or Decimal('0.00')
    fees = payments_data['total_fees'] or Decimal('0.00')

    # 2. Devoluciones
    refunds = OrderReturn.objects.filter(
        organization=organization,
        created_at__range=(start_date, end_date)
    ).aggregate(total=Sum('refund_amount'))['total'] or Decimal('0.00')

    # 3. Costo de Mercancía Vendida (COGS) - Optimizado
    total_cost = Decimal('0.00')
    
    # Usamos select_related para traer el producto de una vez
    items_sold = OrderItem.objects.filter(
        organization=organization,
        order__created_at__range=(start_date, end_date)
    ).select_related('product')

    # Tip de Arquitectura: Podríamos usar una subconsulta aquí, 
    # pero para mantenerlo legible, usaremos un caché de costos si hay muchos items iguales
    cost_cache = {}

    for item in items_sold:
        p_id = item.product_id
        if p_id not in cost_cache:
            last_purchase = PurchaseOrderItem.objects.filter(
                product_id=p_id,
                purchase_order__status='RECEIVED'
            ).order_by('-purchase_order__created_at').only('unit_cost').first()
            
            # Fallback: Si no hay compra previa, asumimos margen del 50% (o podrías usar un campo cost en Product)
            cost_cache[p_id] = last_purchase.unit_cost if last_purchase else (item.price_at_order * Decimal('0.5'))
        
        total_cost += (cost_cache[p_id] * item.quantity)

    # 4. Cálculo final
    net_profit = revenue - total_cost - fees - refunds
    
    # Evitar divisiones por cero y asegurar float para el porcentaje
    margin_pct = (net_profit / revenue * 100) if revenue > 0 else Decimal('0.00')
    
    return {
        "revenue": revenue,
        "cogs": total_cost,
        "fees": fees,
        "refunds": refunds,
        "net_profit": net_profit,
        "margin_percentage": round(float(margin_pct), 2)
    }

class ExchangeService:
    @staticmethod
    def get_current_rate():
        today = timezone.localdate()
        
        # 1. Intentar obtener de la base de datos (Ultra rápido)
        rate = ExchangeRate.objects.filter(date=today).first()
        if rate:
            return rate

        # 2. Si no existe, llamar a APIMigo
        print(f"Buscando tipo de cambio en APIMigo para {today}...")
        api_data = APIMigoClient.get_exchange_rate(today.strftime('%Y-%m-%d'))
        
        # 3. Persistir el resultado (aunque sea el fallback) para evitar re-llamadas constantes
        if api_data:
            rate, _ = ExchangeRate.objects.get_or_create(
                date=today,
                defaults={
                    'buy_price': Decimal(str(api_data.get('precio_compra', '0.00'))),
                    'sell_price': Decimal(str(api_data.get('precio_venta', '0.00'))),
                    'origin': 'apimigo' if api_data.get('success') else 'fallback'
                }
            )
            return rate
        
        return None
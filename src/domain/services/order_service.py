from decimal import Decimal
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404

from ..models import (
    Order, OrderItem, Stock, Product, OrderReturn, 
    Payment, PurchaseOrderItem, ExchangeRate
)
from ...infrastructure.services.apimigo import APIMigoClient
from ..tasks.reporting_tasks import generate_order_pdf_task

# --- SERVICIOS DE CONSULTA Y REPORTES ---

def calculate_expected_cash(organization, start_date, end_date):
    """Calcula el efectivo esperado: Pagos - Reembolsos."""
    # El TenantManager (objects) ya filtra por organización automáticamente
    total_payments = Payment.objects.filter(
        payment_date__range=(start_date, end_date)
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    total_refunds = OrderReturn.objects.filter(
        created_at__range=(start_date, end_date)
    ).aggregate(total=Sum('refund_amount'))['total'] or Decimal('0.00')
    
    return total_payments - total_refunds

def get_net_margin_report(organization, start_date, end_date):
    """Genera reporte de margen neto con COGS (Costo de ventas)."""
    
    payments_data = Payment.objects.filter(
        payment_date__range=(start_date, end_date)
    ).aggregate(
        total_revenue=Sum('amount'),
        total_fees=Sum('fee_amount')
    )
    
    revenue = payments_data['total_revenue'] or Decimal('0.00')
    fees = payments_data['total_fees'] or Decimal('0.00')

    refunds = OrderReturn.objects.filter(
        created_at__range=(start_date, end_date)
    ).aggregate(total=Sum('refund_amount'))['total'] or Decimal('0.00')

    # Cálculo de COGS (Cost of Goods Sold)
    total_cost = Decimal('0.00')
    items_sold = OrderItem.objects.filter(
        order__created_at__range=(start_date, end_date)
    ).select_related('product')

    cost_cache = {}
    for item in items_sold:
        p_id = item.product_id
        if p_id not in cost_cache:
            # Buscamos el costo de la última compra recibida
            last_purchase = PurchaseOrderItem.objects.filter(
                product_id=p_id,
                purchase_order__status='RECEIVED'
            ).order_by('-purchase_order__created_at').only('unit_cost').first()
            
            # Heurística: Si no hay historial, estimamos 50% de margen
            cost_cache[p_id] = last_purchase.unit_cost if last_purchase else (item.price_at_order * Decimal('0.5'))
        
        total_cost += (cost_cache[p_id] * item.quantity)

    # Fórmula Financiera
    # $$NetProfit = Revenue - COGS - Fees - Refunds$$
    net_profit = revenue - total_cost - fees - refunds
    margin_pct = (net_profit / revenue * 100) if revenue > 0 else Decimal('0.00')
    
    return {
        "revenue": revenue,
        "cogs": total_cost,
        "fees": fees,
        "refunds": refunds,
        "net_profit": net_profit,
        "margin_percentage": round(float(margin_pct), 2)
    }

# --- SERVICIOS DE INFRAESTRUCTURA COMPARTIDA ---

class ExchangeService:
    """Servicio compartido para Tipo de Cambio (Global, no Tenant)."""
    @staticmethod
    def get_current_rate():
        today = timezone.localdate()
        
        # Al no ser TenantModel, usamos el manager normal
        rate = ExchangeRate.objects.filter(date=today).first()
        if rate:
            return rate

        api_data = APIMigoClient.get_exchange_rate(today.strftime('%Y-%m-%d'))
        
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

# --- SERVICIOS DE ORDENES Y CATALOGO ---

class OrderService:

    @staticmethod
    @transaction.atomic
    def create_order(organization, customer_data, items_data):
        """Crea una orden validando stock y delegando el descuento al signal."""
        
        order = Order.objects.create(
            organization=organization,
            customer_name=customer_data['name'],
            customer_email=customer_data['email'],
            status='PENDING'
        )

        running_subtotal = Decimal('0.00')

        for item in items_data:
            product = item['product']
            qty = item['quantity']

            # Validamos existencia y cantidad disponible
            stock_record = Stock.objects.filter(product=product).first()
            
            if not stock_record or stock_record.quantity < qty:
                raise ValueError(f"Stock insuficiente para {product.name} (Disponible: {stock_record.quantity if stock_record else 0})")

            current_price = Decimal(str(product.price))
            
            # Al crear este objeto, Django dispara el signal 'adjust_stock_on_sale'
            OrderItem.objects.create(
                organization=organization,
                order=order,
                product=product,
                quantity=qty,
                price_at_order=current_price
            )
            
            running_subtotal += (current_price * Decimal(str(qty)))

        # Cálculos Financieros
        tax_rate = Decimal(str(order.get_tax_rate))
        order.subtotal = running_subtotal
        order.tax_amount = (running_subtotal * (tax_rate / 100)).quantize(Decimal('0.01'))
        order.total_amount = order.subtotal + order.tax_amount
        order.save()

        # Generación de PDF asíncrona
        transaction.on_commit(lambda: generate_order_pdf_task.delay(order.id))

        return order

    @staticmethod
    @transaction.atomic
    def process_return(organization, order_id, product_id, quantity, reason, notes=""):
        """Procesa la devolución de un producto."""
        if quantity <= 0:
            raise ValidationError("La cantidad debe ser mayor a cero.")
        
        # El manager 'objects' garantiza que no se procesen órdenes de otros tenants
        order = get_object_or_404(Order, id=order_id)
        product = get_object_or_404(Product, id=product_id)

        order_item = order.items.filter(product=product).first()
        if not order_item:
            raise ValidationError(f"El producto {product.name} no pertenece a esta orden.")
        
        # Validar que no se devuelva más de lo comprado
        already_returned = OrderReturn.objects.filter(
            order=order, product=product
        ).aggregate(total=Sum('quantity'))['total'] or 0

        if quantity > (order_item.quantity - already_returned):
            raise ValidationError("La cantidad excede el disponible para devolución.")

        return OrderReturn.objects.create(
            organization=organization,
            order=order,
            product=product,
            quantity=quantity,
            reason=reason,
            notes=notes
        )
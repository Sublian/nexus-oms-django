from itertools import product
from decimal import Decimal

from django.db.models import Sum
from django.db import transaction
from django.core.exceptions import ValidationError

from ..models import Order, OrderItem, Stock, Product, TaxConfiguration, OrderReturn, Warehouse, Payment, PurchaseOrderItem

class CatalogService:
    @staticmethod
    def create_product(organization, name, sku, price, category=None):
        """
        Lógica de negocio para crear un producto.
        Aquí podríamos añadir validaciones extra, como verificar 
        si el SKU ya existe para esa organización específica.
        """
        if price < 0:
            raise ValueError("El precio no puede ser negativo")
            
        product = Product.objects.create(
            organization=organization,
            name=name,
            sku=sku,
            price=price,
            category=category
        )
        return product
    
class OrderService:

    @staticmethod
    def process_order(order_id):
        from ..tasks import process_order_notifications
        process_order_notifications.delay(order_id)
        return True

    @staticmethod
    def handle_return(return_id):
        from .tasks import alert_unusual_return_task
        alert_unusual_return_task.delay(return_id)
        
    @staticmethod
    @transaction.atomic
    def create_order(organization, customer_data, items_data):
        tax_config = TaxConfiguration.objects.filter(organization=organization, is_default=True).first()
        tax_rate = tax_config.rate if tax_config else 0

        order = Order.objects.create(
            organization=organization,
            customer_name=customer_data['name'],
            customer_email=customer_data['email']
        )

        subtotal = 0
        for item in items_data:
            product = item['product']
            qty = item['quantity']

            stock_record = Stock.objects.filter(product=product, organization=organization).first()
            if not stock_record or stock_record.quantity < qty:
                raise ValueError(f"Stock insuficiente para {product.name}")

            # Descontar stock (Esto sí se queda aquí porque no tenemos signal de "venta")
            stock_record.quantity -= qty
            stock_record.save()

            OrderItem.objects.create(
                organization=organization,
                order=order,
                product=product,
                quantity=qty,
                price_at_order=product.price
            )
            subtotal += product.price * qty

        order.subtotal = subtotal
        order.tax_amount = (subtotal * tax_rate) / 100
        order.total_amount = order.subtotal + order.tax_amount
        order.save()

        # FIX: Llamada correcta al método estático
        OrderService.process_order(order.id)
        return order

    @staticmethod
    @transaction.atomic
    def process_return(organization, order_id, product_id, quantity, reason, notes=""):
        if quantity <= 0:
            raise ValidationError("La cantidad a devolver debe ser mayor a cero.")
        
        try:
            order = Order.objects.get(id=order_id, organization=organization)
            product = Product.objects.get(id=product_id, organization=organization)
        except (Order.DoesNotExist, Product.DoesNotExist):
            raise ValueError("Orden o Producto no encontrado en esta organización.")

        order_item = order.items.filter(product=product).first()
        if not order_item:
            raise ValidationError(f"El producto {product.name} no pertenece al pedido.")
        
        already_returned = OrderReturn.objects.filter(
            order=order, product=product
        ).aggregate(total=Sum('quantity'))['total'] or 0

        max_allowed = order_item.quantity - already_returned
        if quantity > max_allowed:
            raise ValidationError(f"Máximo disponible para devolver: {max_allowed}.")

        # 4. Registro (La SIGNAL en signals.py se encargará del Stock y Kárdex)
        order_return = OrderReturn.objects.create(
            organization=organization,
            order=order,
            product=product,
            quantity=quantity,
            reason=reason,
            notes=notes
        )

        # 5. Alerta asíncrona
        if reason == 'OTHERS':
            OrderService.handle_return(order_return.id)

        return order_return


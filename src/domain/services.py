from itertools import product

from django.db.models import Sum
from django.db import transaction
from django.core.exceptions import ValidationError

from .models import Order, OrderItem, Stock, Product, TaxConfiguration, OrderReturn, Warehouse
from .tasks import alert_unusual_return_task, process_order_notifications


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
    @transaction.atomic
    def create_order(organization, customer_data, items_data):
        """
        items_data: [{'product': p_obj, 'quantity': 2}, ...]
        """
        # 1. Crear el objeto Pedido
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

            # 2. Validar Stock (Simplificado por ahora)
            # Buscamos en cualquier bodega de la organización
            stock_record = Stock.objects.filter(product=product).first()
            if not stock_record or stock_record.quantity < qty:
                raise ValueError(f"Stock insuficiente para {product.name}")

            # 3. Descontar Stock
            stock_record.quantity -= qty
            stock_record.save()

            # 4. Crear línea de pedido
            OrderItem.objects.create(
                organization=organization,
                order=order,
                product=product,
                quantity=qty,
                price_at_order=product.price
            )
            subtotal += product.price * qty

        # 5. Actualizar total del pedido
        order.subtotal = subtotal
        order.tax_amount = (subtotal * tax_rate) / 100
        order.total_amount = order.subtotal + order.tax_amount
        order.save()

        # Disparamos la tarea de Celery (fuera del hilo principal)
        # .delay() la envía a Redis y el worker la toma cuando puede
        process_order_notifications.delay(order.id)
        return order
    

    @staticmethod
    @transaction.atomic
    def process_return(organization, order_id, product_id, quantity, reason, notes=""):

        if quantity <= 0:
            raise ValidationError("La cantidad a devolver debe ser mayor a cero.")
        
        # 1. Obtener y validar el pedido (asegurando que pertenezca a la organización)
        try:
            order = Order.objects.get(id=order_id, organization=organization)
        except Order.DoesNotExist:
            raise ValueError(f"La Orden #{order_id} no existe o no pertenece a esta organización.")

        try:
            product = Product.objects.get(id=product_id, organization=organization)
        except Product.DoesNotExist:
            raise ValueError(f"El Producto #{product_id} no existe o no pertenece a esta organización.")
        
        # 2 VALIDACIÓN DE CANTIDAD ORIGINAL
        # Buscamos cuánto se compró de este producto en el pedido original
        order_item = order.items.filter(product=product).first()

        if not order_item:
            raise ValidationError(f"El producto {product.name} no forma parte del pedido #{order.id}.")
        
        # 3. CONTROL DE DEVOLUCIONES PREVIAS
        # Sumamos lo que ya se devolvió de este producto para este pedido
        already_returned = OrderReturn.objects.filter(
            order=order, 
            product=product
        ).aggregate(total=Sum('quantity'))['total'] or 0

        max_allowed = order_item.quantity - already_returned

        if quantity > max_allowed:
            raise ValidationError(
                f"Operación no permitida. Cantidad comprada: {order_item.quantity}. "
                f"Ya devuelto anteriormente: {already_returned}. "
                f"Máximo disponible para devolver: {max_allowed}."
            )

        # 4. Si pasa la validación, procedemos con el registro
        order_return = OrderReturn.objects.create(
            organization=organization,
            order=order,
            product=product,
            quantity=quantity,
            reason=reason,
            notes=notes
        )

        # 5. Actualización de Stock (en la bodega correspondiente)
        stock_record = Stock.objects.filter(product=product, organization=organization).first()
        if stock_record:
            stock_record.quantity += quantity
            stock_record.save()

        # 6. Alerta asíncrona
        if reason == 'OTHERS':
            from .tasks import alert_unusual_return_task
            alert_unusual_return_task.delay(order_return.id)

        return order_return

from django.db import transaction
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
        # 1. Obtener y validar el pedido (asegurando que pertenezca a la organización)
        try:
            order = Order.objects.get(id=order_id, organization=organization)
        except Order.DoesNotExist:
            raise ValueError(f"La Orden #{order_id} no existe o no pertenece a esta organización.")

        try:
            product = Product.objects.get(id=product_id, organization=organization)
        except Product.DoesNotExist:
            raise ValueError(f"El Producto #{product_id} no existe o no pertenece a esta organización.")

        # 2. Crear el registro de devolución
        order_return = OrderReturn.objects.create(
            organization=organization,
            order=order,
            product=product,
            quantity=quantity,
            reason=reason,
            notes=notes
        )

        # 3. ACTUALIZACIÓN DE INVENTARIO
        # Devolvemos las unidades al producto
        stock_record = Stock.objects.filter(
            product=product, 
            organization=organization
        ).first()
        
        if stock_record:
            stock_record.quantity += quantity
            stock_record.save()
        else:
            # Si no existe registro de stock, lo creamos en una bodega por defecto
            warehouse = Warehouse.objects.filter(organization=organization).first()
            if not warehouse:
                raise ValueError("No hay bodegas configuradas para esta organización.")
                
            Stock.objects.create(
                product=product,
                warehouse=warehouse,
                organization=organization,
                quantity=quantity
            )

        # 4. Disparar alerta si es OTHERS
        if reason == 'OTHERS':
            from .tasks import alert_unusual_return_task
            alert_unusual_return_task.delay(order_return.id)

        return order_return
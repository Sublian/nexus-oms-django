
from django.db import transaction
from .models import Order, OrderItem, Stock, Product


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
        order = Order.objects.create(
            organization=organization,
            customer_name=customer_data['name'],
            customer_email=customer_data['email']
        )

        total = 0
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
            total += product.price * qty

        # 5. Actualizar total del pedido
        order.total_amount = total
        order.save()
        return order
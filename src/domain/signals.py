from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import OrderItem, Stock, StockMovement

@receiver(post_save, sender=OrderItem)
def adjust_stock_on_sale(sender, instance, created, **kwargs):
    if created:
        # Buscamos el stock en la bodega principal de la organización
        # Nota: En un flujo real, la orden debería especificar de qué bodega sale.
        stock = Stock.objects.filter(
            product=instance.product,
            organization=instance.organization
        ).first()

        if stock:
            # 1. Actualizar cantidad neta
            stock.quantity -= instance.quantity
            stock.save()

            # 2. Registrar el movimiento en el Kárdex
            StockMovement.objects.create(
                organization=instance.organization,
                stock=stock,
                quantity=instance.quantity,
                movement_type=StockMovement.MovementType.OUTPUT,
                reason=f"Venta: Pedido #{instance.order.id}",
                order=instance.order
            )
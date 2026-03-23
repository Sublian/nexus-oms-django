from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import OrderItem, Stock, StockMovement, PurchaseOrder

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

@receiver(post_save, sender=PurchaseOrder)
def update_stock_on_received_po(sender, instance, **kwargs):
    # Solo actuamos si la orden pasa a estado RECEIVED
    if instance.status == PurchaseOrder.POStatus.RECEIVED:
        for item in instance.items.all():
            stock, _ = Stock.objects.get_or_create(
                product=item.product,
                warehouse=instance.warehouse,
                organization=instance.organization,
                defaults={'quantity': 0}
            )
            
            # 1. Aumentar Stock neta
            stock.quantity += item.quantity
            stock.save()

            # 2. Registro en el Kárdex
            StockMovement.objects.create(
                organization=instance.organization,
                stock=stock,
                quantity=item.quantity,
                movement_type=StockMovement.MovementType.INPUT,
                reason=f"Compra: OC #{instance.id}",
                # Aquí no hay order de venta vinculada
            )


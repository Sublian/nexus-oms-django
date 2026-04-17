from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from .models import OrderItem, Stock, StockMovement, PurchaseOrder, OrderReturn

@receiver(post_save, sender=OrderItem)
def adjust_stock_on_sale(sender, instance, created, **kwargs):
    """
    Descuenta stock y registra Kárdex cuando se crea un item de pedido.
    """
    if created:
        # Usamos select_for_update para evitar condiciones de carrera en la señal
        stock = Stock.objects.select_for_update().filter(
            product=instance.product,
            organization=instance.organization
        ).first()

        if stock:
            # 1. Actualizar cantidad neta
            stock.quantity -= instance.quantity
            stock.save()

            # 2. Registrar el movimiento en el Kárdex (Salida)
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
    """
    Incrementa stock cuando una Orden de Compra cambia a RECIBIDA.
    """
    if instance.status == PurchaseOrder.POStatus.RECEIVED:
        # Usamos una transacción para asegurar que todos los items se procesen o ninguno
        with transaction.atomic():
            for item in instance.items.all():
                stock, _ = Stock.objects.get_or_create(
                    product=item.product,
                    warehouse=instance.warehouse,
                    organization=instance.organization,
                    defaults={'quantity': 0}
                )
                
                stock.quantity += item.quantity
                stock.save()

                StockMovement.objects.create(
                    organization=instance.organization,
                    stock=stock,
                    quantity=item.quantity,
                    movement_type=StockMovement.MovementType.INPUT,
                    reason=f"Compra: OC #{instance.id}"
                )

@receiver(post_save, sender=OrderReturn)
def handle_stock_on_return(sender, instance, created, **kwargs):
    """
    Reingresa stock cuando se registra una devolución aprobada.
    """
    # Verificamos que sea nuevo y que el negocio haya marcado que el producto reingresa
    if created and getattr(instance, 'reentered_to_stock', True):
        stock = Stock.objects.filter(
            product=instance.product,
            organization=instance.organization
        ).first()

        if stock:
            stock.quantity += instance.quantity
            stock.save()

            StockMovement.objects.create(
                organization=instance.organization,
                stock=stock,
                quantity=instance.quantity,
                movement_type=StockMovement.MovementType.RETURN,
                reason=f"Devolución: Ticket #{instance.id} - Pedido #{instance.order.id}",
                order=instance.order
            )
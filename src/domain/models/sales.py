# Order, OrderItem, OrderReturn, Payment

from django.db import models

from src.infrastructure.models import TenantModel
from .order_constants import OrderStatus


class Order(TenantModel):
    STATUS_CHOICES = OrderStatus.CHOICES
    VALID_TRANSITIONS = OrderStatus.VALID_TRANSITIONS

    class DeliveryType(models.TextChoices):
        PICKUP   = 'PICKUP',   'Retiro en Tienda'
        DELIVERY = 'DELIVERY', 'Delivery'

    client = models.ForeignKey('domain.Client', on_delete=models.PROTECT, related_name='orders', null=True)
    customer_name = models.CharField(max_length=255)
    customer_email = models.EmailField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=OrderStatus.DRAFT)
    delivery_type = models.CharField(max_length=10, choices=DeliveryType.choices, default='PICKUP')
    delivery_address = models.TextField(blank=True, default='')
    shipping_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    # CAMPOS REALES EN DB (Se llenan al crear la orden)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    pdf_report = models.FileField(upload_to='orders/pdfs/', null=True, blank=True)
    nota = models.TextField(blank=True, default='', help_text='Nota de cambios en la orden (por qué se incrementó, decrementó o borró productos)')
    workflow_processed = models.BooleanField(default=False, help_text='Flag que indica si el flujo post-pago ya fue ejecutado')
    workflow_status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pendiente'), ('processing', 'Procesando'), ('completed', 'Completado'), ('failed', 'Fallido')],
        default='pending',
        help_text='Estado del workflow post-pago: pending | processing | completed | failed'
    )
    invoice_status = models.CharField(
        max_length=20,
        choices=[
            ('pending',    'Pendiente'),
            ('processing', 'Procesando'),
            ('issued',     'Emitida'),
            ('retrying',   'Reintentando'),
            ('failed',     'Fallida'),
        ],
        default='pending',
        help_text='Estado de facturación: pending | processing | issued | retrying | failed'
    )
    invoice_external_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='ID externo de factura de Nubefact o Mock'
    )
    invoice_attempts = models.IntegerField(
        default=0,
        help_text='Número de intentos de facturación realizados'
    )
    invoice_last_error = models.TextField(
        blank=True,
        null=True,
        help_text='Último error de facturación (para debugging y retry manual)'
    )

    def __str__(self):
        return f"Pedido {self.id} - {self.customer_name} ({self.organization.name})"
    
    # PROPIEDADES DE APOYO (Sin colisión de nombres)
    @property
    def get_tax_rate(self):
        """Busca la tasa de impuesto configurada para la organización."""
        from .config import TaxConfiguration
        config = TaxConfiguration.objects.filter(
            organization=self.organization, 
            is_default=True
        ).first()
        # Fallback al 18% si no hay configuración (común en Perú/IGV)
        return config.rate if config else 18.00


class OrderItem(TenantModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('domain.Product', on_delete=models.PROTECT) # No borrar producto si hay pedidos
    quantity = models.PositiveIntegerField()
    price_at_order = models.DecimalField(max_digits=10, decimal_places=2) # Histórico del precio

    @property
    def total_price(self):
        return self.quantity * self.price_at_order
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name}"


class OrderReturn(TenantModel):
    class Reason(models.TextChoices):
        DAMAGED = 'DAMAGED', 'Producto Dañado (No reingresa)'
        MISTAKE = 'MISTAKE', 'Error en Envío'
        DISSATISFIED = 'DISSATISFIED', 'Cliente Insatisfecho'
        EXPIRED = 'EXPIRED', 'Producto Vencido'
        OTHERS = 'OTHERS', 'Otros'

    order = models.ForeignKey(
        Order, 
        on_delete=models.PROTECT, # Protegemos para no borrar registros contables
        related_name='returns'
    )
    product = models.ForeignKey('domain.Product', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    reason = models.CharField(
        max_length=20, 
        choices=Reason.choices, 
        default=Reason.DISSATISFIED
    )
    notes = models.TextField(blank=True, null=True)
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reentered_to_stock = models.BooleanField(default=True) # ¿Volvió a la estantería?
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Devolución"
        verbose_name_plural = "Devoluciones"

    def __str__(self):
        return f"Retorno #{self.id} - Pedido #{self.order.id} ({self.product.sku})"
    

class Payment(TenantModel):
    class PaymentMethod(models.TextChoices):
        CASH = 'CASH', 'Efectivo'
        CREDIT_CARD = 'CARD', 'Tarjeta de Crédito/Débito'
        TRANSFER = 'TRANSFER', 'Transferencia Bancaria'
        DIGITAL_WALLET = 'WALLET', 'Billetera Digital (Yape/Plin)'

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    method = models.CharField(max_length=10, choices=PaymentMethod.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_reference = models.CharField(max_length=100, blank=True, null=True)
    payment_date = models.DateTimeField(auto_now_add=True)
    
    # Para realismo: ¿Hubo comisión? (Ej: 3.5% de Niubiz/Izipay)
    fee_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"Pago {self.method} - {self.amount} (Pedido {self.order.id})"

    @property
    def net_amount(self):
        return self.amount - self.fee_amount





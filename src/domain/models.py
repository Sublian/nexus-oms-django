# src\domain\models.py
import uuid

from django.db import models

from src.infrastructure.models import TenantModel



class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True) # Para la URL: nexus.com/empresa-a
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    telegram_enabled = models.BooleanField(default=False)
    whatsapp_enabled = models.BooleanField(default=False)
    admin_email = models.EmailField()

    def __str__(self):
        return self.name

    
class Category(TenantModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return f"{self.name} ({self.organization.name})"

class Product(TenantModel):
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.sku}"    
    
class Warehouse(TenantModel):
    name = models.CharField(max_length=100)
    address = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.organization.name})"

class Stock(TenantModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stocks')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stocks')
    quantity = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'warehouse') # Un registro por producto en cada bodega

    def __str__(self):
        return f"{self.product.name} @ {self.warehouse.name}: {self.quantity}"
    
class TaxConfiguration(TenantModel):
    name = models.CharField(max_length=50) # Ej: "IGV Perú", "IVA España"
    rate = models.DecimalField(max_digits=5, decimal_places=2) # Ej: 18.00
    is_default = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.rate}%)"
    
class Order(TenantModel):
    STATUS_CHOICES = [
        ('PENDING', 'Pendiente'),
        ('PAID', 'Pagado'),
        ('SHIPPED', 'Enviado'),
        ('DELIVERED', 'Entregado'),
        ('CANCELLED', 'Cancelado'),
    ]

    customer_name = models.CharField(max_length=255)
    customer_email = models.EmailField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pedido {self.id} - {self.customer_name} ({self.organization.name})"

class OrderItem(TenantModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT) # No borrar producto si hay pedidos
    quantity = models.PositiveIntegerField()
    price_at_order = models.DecimalField(max_digits=10, decimal_places=2) # Histórico del precio

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"


class SalesReport(TenantModel):
    generated_at = models.DateTimeField(auto_now_add=True)
    total_sales = models.DecimalField(max_digits=15, decimal_places=2)
    order_count = models.IntegerField()
    data = models.JSONField() # Guardaremos el desglose aquí

    def __str__(self):
        return f"Reporte {self.generated_at} - {self.organization.name}"
    

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
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
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
    

class StockMovement(TenantModel):
    class MovementType(models.TextChoices):
        INPUT = 'INPUT', 'Ingreso (Compra/Ajuste)'
        OUTPUT = 'OUTPUT', 'Egreso (Venta/Ajuste)'
        RETURN = 'RETURN', 'Devolución'

    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='movements')
    quantity = models.IntegerField()  # Siempre positivo, el tipo define el signo
    movement_type = models.CharField(max_length=10, choices=MovementType.choices)
    reason = models.CharField(max_length=255)  # Ej: "Venta Pedido #102", "Carga Inicial"
    
    # Relación opcional para saber qué orden generó este movimiento
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.movement_type} - {self.stock.product.name} ({self.quantity})"


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


class Supplier(TenantModel):
    name = models.CharField(max_length=255)
    ruc = models.CharField(max_length=20, blank=True, null=True) # Registro Tributario
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.name} ({self.organization.name})"

class PurchaseOrder(TenantModel):
    class POStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pendiente'
        RECEIVED = 'RECEIVED', 'Recibido'
        CANCELLED = 'CANCELLED', 'Cancelado'

    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_orders')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=POStatus.choices, default=POStatus.PENDING)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"OC #{self.id} - {self.supplier.name}"

class PurchaseOrderItem(TenantModel):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2) # ¿A cuánto lo compramos?

    def __str__(self):
        return f"{self.quantity} x {self.product.name} (Costo: {self.unit_cost})"


class CashReconciliation(TenantModel):
    opened_at = models.DateTimeField()
    closed_at = models.DateTimeField(auto_now_add=True)
    
    # Lo que el sistema calculó
    expected_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    # Lo que el cajero contó físicamente
    actual_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Calculado: actual - expected
    difference = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    
    notes = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        # Lógica de negocio: Calcular diferencia antes de guardar
        self.difference = self.actual_amount - self.expected_amount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Arqueo {self.organization.name} - {self.closed_at.date()}"




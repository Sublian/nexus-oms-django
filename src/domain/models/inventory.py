# Product, Stock, Warehouse, Supplier, PurchaseOrder
from django.db import models

from src.infrastructure.models import TenantModel
from src.domain.models import Order

 
class Category(TenantModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return f"{self.name} ({self.organization.name})"


class Supplier(TenantModel):
    name = models.CharField(max_length=255)
    ruc = models.CharField(max_length=20, blank=True, null=True) # Registro Tributario
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)

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

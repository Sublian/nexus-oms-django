import uuid

from django.db import models

from src.infrastructure.models import TenantModel

class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True) # Para la URL: nexus.com/empresa-a
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

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
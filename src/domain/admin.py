from django.contrib import admin
from .models import Organization, Category, Product, Order, OrderItem

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'created_at')
    prepopulated_fields = {'slug': ('name',)} # Esto auto-rellena el slug mientras escribes el nombre

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization')
    list_filter = ('organization',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'price', 'organization', 'is_active')
    list_filter = ('organization', 'category')
    search_fields = ('name', 'sku')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_name', 'total_amount', 'status', 'organization')
    inlines = [OrderItemInline]
    list_filter = ('organization', 'status')
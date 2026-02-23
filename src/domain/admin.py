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

class TenantAdmin(admin.ModelAdmin):
    """Clase base para que el Admin solo muestre datos de la organización del usuario"""
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Aquí filtraríamos por la organización asignada al usuario del admin
        return qs

# En el OrderItemInline, debemos limitar los productos que aparecen en el combo
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "product":
            # Si estamos editando un pedido de Nike, solo mostrar productos de Nike
            parent_order_id = request.resolver_match.kwargs.get('object_id')
            if parent_order_id:
                order = Order.objects.get(pk=parent_order_id)
                kwargs["queryset"] = Product.objects.filter(organization=order.organization)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_name', 'total_amount', 'status', 'organization')
    inlines = [OrderItemInline]
    list_filter = ('organization', 'status')
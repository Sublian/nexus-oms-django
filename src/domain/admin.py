from django.contrib import admin
from django.utils.html import format_html

from .models import Organization, Category, Product, Order, OrderItem
from .models.invoicing import InvoiceSyncQueue
from .models.config import CompanyInvoiceConfig
from .invoice_status_ui import get_invoice_status_ui


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'created_at')
    prepopulated_fields = {'slug': ('name',)}


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
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "product":
            parent_order_id = request.resolver_match.kwargs.get('object_id')
            if parent_order_id:
                order = Order.objects.get(pk=parent_order_id)
                kwargs["queryset"] = Product.objects.filter(organization=order.organization)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_name', 'total_amount', 'status', 'invoice_status_badge', 'organization')
    list_filter = ('organization', 'status', 'invoice_status')
    inlines = [OrderItemInline]

    @admin.display(description='Facturación')
    def invoice_status_badge(self, obj):
        ui = get_invoice_status_ui(obj.invoice_status)
        return format_html(
            '<span style="padding:2px 8px;border-radius:9999px;font-size:11px;font-weight:700;">'
            '{}</span>',
            ui['label'],
        )


@admin.register(InvoiceSyncQueue)
class InvoiceSyncQueueAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'order_link', 'organization', 'status',
        'attempts', 'last_attempt_at', 'next_retry_at', 'created_at',
    )
    list_filter   = ('status', 'organization', 'created_at')
    search_fields = ('order__id', 'last_error')
    readonly_fields = (
        'created_at', 'locked_at', 'last_attempt_at',
        'completed_at', 'exhausted_at', 'last_response', 'last_error',
    )
    ordering = ('-created_at',)
    actions  = ['retry_failed_invoices']

    @admin.display(description='Orden')
    def order_link(self, obj):
        return format_html('<a href="/admin/domain/order/{}/change/">#{}</a>', obj.order_id, obj.order_id)

    @admin.action(description='Reencolar para reintento manual')
    def retry_failed_invoices(self, request, queryset):
        retryable = queryset.filter(status__in=list(InvoiceSyncQueue.RETRYABLE_STATUSES))
        count = 0
        for entry in retryable:
            entry.requeue()
            entry.save(update_fields=[
                'status', 'locked_at', 'exhausted_at', 'last_error', 'next_retry_at',
            ])
            count += 1
        skipped = queryset.count() - count
        msg = f'{count} factura(s) reencoladas para reintento.'
        if skipped:
            msg += f' {skipped} omitida(s) por no estar en estado retryable.'
        self.message_user(request, msg)


@admin.register(CompanyInvoiceConfig)
class CompanyInvoiceConfigAdmin(admin.ModelAdmin):
    list_display  = ('organization', 'provider_type', 'api_base_url', 'enabled')
    list_filter   = ('provider_type', 'organization', 'enabled')
    search_fields = ('organization__name',)
    readonly_fields = ('organization',)

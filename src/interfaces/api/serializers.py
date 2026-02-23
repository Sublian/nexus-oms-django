from rest_framework import serializers

from src.domain.models import Product, Category, SalesReport
from django.db.models import Sum

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description']

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source='category.name')
    stock_total = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'sku', 'price', 'category_name', 'stock_total', 'is_active']

    def get_stock_total(self, obj):
        # Sumamos el stock de todas las bodegas de este producto
        return obj.stocks.aggregate(total=Sum('quantity'))['total'] or 0
    
class OrderItemCreateSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)

class OrderCreateSerializer(serializers.Serializer):
    customer_name = serializers.CharField(max_length=255)
    customer_email = serializers.EmailField()
    items = OrderItemCreateSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Un pedido debe tener al menos un producto.")
        return value
    
class SalesReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesReport
        fields = ['id', 'generated_at', 'total_sales', 'order_count', 'data']


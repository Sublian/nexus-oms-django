from rest_framework import serializers

from src.domain.models import Product, Category
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
    
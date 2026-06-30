from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from src.domain.models import OrderReturn, Product, Category, SalesReport
from django.db.models import Sum

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'description']

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source='category.name')
    stock_total = serializers.IntegerField(read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'sku', 'price', 'category_name', 'stock_total', 'is_active']

    
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

class ReportTriggerSerializer(serializers.Serializer):
    start_date = serializers.DateTimeField(required=False, help_text="Fecha inicio (ISO 8601)")
    end_date = serializers.DateTimeField(required=False, help_text="Fecha fin (ISO 8601)")
    notes = serializers.CharField(max_length=255, required=False, help_text="Notas adicionales para el reporte")
    
    # Esto limpia los datos de ejemplo en Swagger
    class Meta:
        ref_name = "ReportTrigger"

        
class OrderReturnSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderReturn
        fields = ['id', 'order', 'product', 'quantity', 'reason', 'notes', 'created_at']
        read_only_fields = ['id', 'created_at']


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Extiende el token JWT con claims del tenant y rol del usuario."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        token['role'] = user.role
        token['organization_id'] = str(user.organization_id) if user.organization_id else None
        return token


class PaymentProcessSerializer(serializers.Serializer):
    """
    Validación de entrada para el procesamiento de pagos desde la API REST.
    Replica las opciones nativas del modelo de datos de pagos.
    """
    method = serializers.ChoiceField(choices=[('CASH', 'Efectivo'), ('CARD', 'Tarjeta')])
    reference = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)

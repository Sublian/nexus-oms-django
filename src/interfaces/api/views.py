from rest_framework import viewsets
from src.domain.models import Product
from .serializers import ProductSerializer

class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API para ver productos. 
    El aislamiento de datos es automático gracias al TenantManager.
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
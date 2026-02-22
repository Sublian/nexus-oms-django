from rest_framework import viewsets
from src.domain.models import Product

from .serializers import ProductSerializer
from src.infrastructure.multitenancy.thread_local import get_current_organization

class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API para ver productos. 
    El aislamiento de datos es automático gracias al TenantManager.
    """
    # queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def get_queryset(self):
        # Si el TenantManager está activo, Product.objects.all() ya viene filtrado.
        # Pero si queremos forzar ver todo (ej: Admin Central):
        org_id = get_current_organization()
        
        if not org_id:
            # Si no hay organización en el contexto, devolvemos todo usando el manager 'all_objects'
            # que definimos en el TenantModel
            return Product.all_objects.all()
            
        return Product.objects.all()
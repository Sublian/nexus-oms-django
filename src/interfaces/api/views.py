from rest_framework import viewsets, status
from rest_framework.response import Response

from src.domain.models import Order, Product, Organization
from src.domain.services import OrderService
from .serializers import OrderCreateSerializer, ProductSerializer
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
    
class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderCreateSerializer # Por ahora para el POST

    def create(self, request, *args, **kwargs):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Obtener la organización del contexto (Middleware)
        org_id = get_current_organization()
        organization = Organization.objects.get(id=org_id)

        # Preparar los datos para el servicio
        items_data = []
        try:
            for item in serializer.validated_data['items']:
                # El TenantManager asegura que solo encuentre productos de esta organización
                product = Product.objects.get(id=item['product_id'])
                items_data.append({
                    'product': product,
                    'quantity': item['quantity']
                })
            
            # Llamar al servicio de dominio
            order = OrderService.create_order(
                organization=organization,
                customer_data={
                    'name': serializer.validated_data['customer_name'],
                    'email': serializer.validated_data['customer_email']
                },
                items_data=items_data
            )
            
            return Response({"order_id": order.id, "total": order.total_amount}, status=status.HTTP_201_CREATED)
            
        except Product.DoesNotExist:
            return Response({"error": "Uno de los productos no existe en tu organización"}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
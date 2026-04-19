from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, status, serializers as drf_serializers
from django.shortcuts import get_object_or_404, render
from rest_framework.response import Response
from rest_framework.decorators import action
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Sum
from django.db.models.functions import Coalesce

from src.domain.models import Order, Product, Organization, SalesReport, OrderReturn
from src.domain.services import OrderService
from src.domain.tasks import generate_sales_report_task
from src.infrastructure.multitenancy.thread_local import get_current_organization, set_current_organization
from .serializers import (
    OrderCreateSerializer, ProductSerializer, 
    ReportTriggerSerializer, SalesReportSerializer, 
    OrderReturnSerializer
)

# --- Vistas HTMX / Web ---

def organization_settings_view(request, org_slug):
    """
    Gestiona la configuración de la organización mediante HTMX.
    """
    org = get_object_or_404(Organization, slug=org_slug)
    
    # Sincronizamos el thread_local para asegurar aislamiento en la lógica interna
    set_current_organization(org.id)

    if request.method == "POST":
        org.telegram_enabled = 'telegram_enabled' in request.POST
        org.whatsapp_enabled = 'whatsapp_enabled' in request.POST
        org.admin_email = request.POST.get('admin_email', org.admin_email)
        org.save()
        
        return render(request, 'organizations/settings.html', {
            'org': org, 
            'org_slug': org_slug,
            'message': '✅ Configuración guardada correctamente'
        })

    return render(request, 'organizations/settings.html', {
        'org': org,
        'org_slug': org_slug
    })

# --- ViewSets de la API ---

class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API para consulta de productos.
    El aislamiento es automático gracias al TenantManager.
    """
    serializer_class = ProductSerializer

    def get_queryset(self):
        org_id = get_current_organization()
        # Si hay un tenant activo, 'objects' ya filtra automáticamente.
        # Si no lo hay (Admin Central), usamos 'all_objects'.
        if not org_id:
            queryset = Product.all_objects.all()
        else:
            queryset = Product.objects.all()
        
        # 'stocks__quantity' es el camino desde Producto hasta el modelo Stock
        # Coalesce sirve para que si no hay stock, devuelva 0 en lugar de None
        return queryset.annotate(
            stock_total=Coalesce(Sum('stocks__quantity'), 0)
        )

class OrderViewSet(viewsets.ModelViewSet):
    """
    Gestión de pedidos con validación de pertenencia al Tenant.
    """
    serializer_class = OrderCreateSerializer

    def get_queryset(self):
        org_id = get_current_organization()
        if not org_id:
            return Order.all_objects.all()
        return Order.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        org_id = get_current_organization()
        organization = get_object_or_404(Organization, id=org_id)

        items_data = []
        try:
            for item in serializer.validated_data['items']:
                # El TenantManager asegura que solo se encuentren productos 
                # que pertenecen a esta organización.
                product = Product.objects.get(id=item['product_id'])
                items_data.append({
                    'product': product,
                    'quantity': item['quantity']
                })
            
            # Delegamos la creación y lógica de negocio al Servicio de Dominio
            order = OrderService.create_order(
                organization=organization,
                customer_data={
                    'name': serializer.validated_data['customer_name'],
                    'email': serializer.validated_data['customer_email']
                },
                items_data=items_data
            )
            
            return Response({
                "order_id": order.id, 
                "total": order.total_amount
            }, status=status.HTTP_201_CREATED)
            
        except Product.DoesNotExist:
            return Response(
                {"error": "Uno o más productos no existen en su organización."}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except (ValueError, DjangoValidationError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ReportViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Consulta y disparo de reportes de ventas asíncronos.
    """
    serializer_class = SalesReportSerializer 
    
    def get_queryset(self):
        org_id = get_current_organization()
        if not org_id:
            return SalesReport.all_objects.all()
        return SalesReport.objects.all()
    
    @extend_schema(
        request=ReportTriggerSerializer,
        responses={202: drf_serializers.DictField()}, 
        description="Dispara la generación asíncrona de un reporte de ventas vía Celery."
    )
    @action(detail=False, methods=['post'])
    def trigger_report(self, request):
        org_id = get_current_organization()
        serializer = ReportTriggerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        start_date = serializer.validated_data.get('start_date')
        end_date = serializer.validated_data.get('end_date')

        # Lanzamos la tarea a Celery
        task = generate_sales_report_task.delay(org_id, start_date, end_date)
        
        return Response({
            "message": "Generación de reporte iniciada",
            "task_id": task.id,
            "status": "PENDING"
        }, status=status.HTTP_202_ACCEPTED)

class OrderReturnViewSet(viewsets.ModelViewSet):
    """
    API para gestionar devoluciones de productos.
    """
    serializer_class = OrderReturnSerializer
    
    def get_queryset(self):
        org_id = get_current_organization()
        if not org_id:
            return OrderReturn.all_objects.all()
        return OrderReturn.objects.all()
    
    @extend_schema(
        summary="Registrar devolución y recuperar stock",
        description="Crea un registro de devolución y actualiza el inventario automáticamente."
    )
    def create(self, request, *args, **kwargs):
        org_id = get_current_organization()

        # Si org_id es None, el middleware no está haciendo su trabajo o falta contexto
        if not org_id:
            return Response(
                {"error": "No se identificó una organización activa (Tenant missing)"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        organization = get_object_or_404(Organization, id=org_id)

        try:
            # Procesamiento a través del servicio de dominio para asegurar consistencia
            order_return = OrderService.process_return(
                organization=organization,
                order_id=request.data.get('order'),
                product_id=request.data.get('product'),
                quantity=int(request.data.get('quantity')),
                reason=request.data.get('reason'),
                notes=request.data.get('notes', "")
            )
            
            serializer = self.get_serializer(order_return)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except (DjangoValidationError, ValueError) as e:
            message = e.message if hasattr(e, 'message') else str(e)
            return Response({"error": message}, status=status.HTTP_400_BAD_REQUEST)
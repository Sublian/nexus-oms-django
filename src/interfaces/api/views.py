from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, status, serializers as drf_serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from rest_framework_simplejwt.views import TokenObtainPairView

from django.shortcuts import get_object_or_404, render
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.db import transaction
from django.utils import timezone
from decimal import Decimal

from src.domain.models import Order, Product, Organization, SalesReport, OrderReturn, Payment
from src.domain.models.order_constants import OrderStatus
from src.domain.services import OrderService
from src.domain.services.order_service import OrderWorkflowService
from src.domain.tasks import generate_sales_report_task
from src.infrastructure.multitenancy.context import set_current_organization
import logging
workflow_logger = logging.getLogger(__name__)

from .serializers import (
    OrderCreateSerializer, ProductSerializer,
    ReportTriggerSerializer, SalesReportSerializer,
    OrderReturnSerializer, CustomTokenObtainPairSerializer,
    PaymentProcessSerializer,
)


class CustomTokenObtainPairView(TokenObtainPairView):
    """Login: devuelve access + refresh token con claims del tenant."""
    permission_classes = [AllowAny]
    serializer_class = CustomTokenObtainPairSerializer


# ── Mixin de aislamiento por tenant ──────────────────────────────────────────

class TenantViewMixin:
    """
    Resuelve la organización activa desde el usuario autenticado.
    Superusuarios REQUIEREN un header X-Org-ID explícito (Opción C: fail-secure).
    """
    def get_organization(self):
        user = self.request.user
        if user.is_superuser:
            org_id = self.request.META.get('HTTP_X_ORG_ID')
            if not org_id:
                raise PermissionDenied(
                    "Administrative access requires an explicit X-Org-ID header context."
                )
            return get_object_or_404(Organization, id=org_id)
        return user.organization


# ── Vista Web (HTMX) — sin JWT, usa slug de URL ──────────────────────────────

def organization_settings_view(request, org_slug):
    org = get_object_or_404(Organization, slug=org_slug)
    set_current_organization(org.id)

    if request.method == "POST":
        org.telegram_enabled = 'telegram_enabled' in request.POST
        org.whatsapp_enabled = 'whatsapp_enabled' in request.POST
        org.admin_email = request.POST.get('admin_email', org.admin_email)
        org.save()

        return render(request, 'organizations/settings.html', {
            'org': org,
            'org_slug': org_slug,
            'message': '✅ Configuración guardada correctamente',
        })

    return render(request, 'organizations/settings.html', {
        'org': org,
        'org_slug': org_slug,
    })


# ── ViewSets de la API ────────────────────────────────────────────────────────

class ProductViewSet(TenantViewMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductSerializer

    def get_queryset(self):
        org = self.get_organization()
        return Product.objects.filter(organization=org).annotate(
            stock_total=Coalesce(Sum('stocks__quantity'), 0)
        )


class OrderViewSet(TenantViewMixin, viewsets.ModelViewSet):
    serializer_class = OrderCreateSerializer

    def get_queryset(self):
        org = self.get_organization()
        return Order.objects.filter(organization=org)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization = self.get_organization()
        try:
            items_data = []
            for item in serializer.validated_data['items']:
                product = Product.objects.get(id=item['product_id'])
                items_data.append({'product': product, 'quantity': item['quantity']})

            order = OrderService.create_order(
                organization=organization,
                customer_data={
                    'name': serializer.validated_data['customer_name'],
                    'email': serializer.validated_data['customer_email'],
                },
                items_data=items_data,
            )

            return Response(
                {'order_id': order.id, 'total': order.total_amount},
                status=status.HTTP_201_CREATED,
            )

        except Product.DoesNotExist:
            return Response(
                {'error': 'Uno o más productos no existen en su organización.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except (ValueError, DjangoValidationError) as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='pay')
    def process_api_payment(self, request, pk=None):
        """
        Endpoint REST que estandariza la vista web tradicional 'order_pay_modal_view'.
        Sostiene el aislamiento multi-tenant y la lógica transaccional de cobros.
        """
        order = self.get_object()
        tenant = self.get_organization()

        # 1. Validar FSM (Máquina de estados): Control de transiciones permitidas
        if "PAID" not in order.VALID_TRANSITIONS.get(order.status, []):
            return Response(
                {"error": f"Transición de estado no permitida desde {order.status} hacia PAID."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = PaymentProcessSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        method = serializer.validated_data['method']
        reference = serializer.validated_data.get('reference', '').strip() or None

        # 2. Replicar la regla de negocio financiera de cálculo de comisiones (Fees)
        if method == 'CARD':
            fee = (order.total_amount * Decimal('0.035')).quantize(Decimal('0.01'))
        else:
            fee = Decimal('0.00')

        # 3. Transacción atómica combinada con el workflow del dominio
        try:
            with transaction.atomic():
                payment, created = Payment.objects.get_or_create(
                    order=order,
                    defaults={
                        'organization': tenant,
                        'method': method,
                        'amount': order.total_amount,
                        'transaction_reference': reference,
                        'fee_amount': fee,
                        'payment_date': timezone.now(),
                    },
                )

                if not created:
                    return Response(
                        {"error": "Ya existe un registro de pago asociado a este pedido."},
                        status=status.HTTP_409_CONFLICT
                    )

                # Mutación de estado de la orden dentro del límite transaccional
                order.status = "PAID"

                # Orquestación obligatoria post-pago usando el servicio del dominio
                workflow = OrderWorkflowService(workflow_logger)
                workflow.handle_order_paid(order)

                order.save()

            return Response(
                {
                    "message": "Pago procesado y asimilado en el flujo del MVP con éxito.",
                    "order_id": order.id,
                    "status": order.status,
                    "fee_applied": float(fee)
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {"error": f"Error crítico de persistencia en base de datos: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReportViewSet(TenantViewMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = SalesReportSerializer

    def get_queryset(self):
        org = self.get_organization()
        return SalesReport.objects.filter(organization=org)

    @extend_schema(
        request=ReportTriggerSerializer,
        responses={202: drf_serializers.DictField()},
        description="Dispara la generación asíncrona de un reporte de ventas vía Celery.",
    )
    @action(detail=False, methods=['post'])
    def trigger_report(self, request):
        organization = self.get_organization()
        serializer = ReportTriggerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        start_date = serializer.validated_data.get('start_date')
        end_date = serializer.validated_data.get('end_date')

        task = generate_sales_report_task.delay(str(organization.id), start_date, end_date)

        return Response({
            'message': 'Generación de reporte iniciada',
            'task_id': task.id,
            'status': 'PENDING',
        }, status=status.HTTP_202_ACCEPTED)


class OrderReturnViewSet(TenantViewMixin, viewsets.ModelViewSet):
    serializer_class = OrderReturnSerializer

    def get_queryset(self):
        org = self.get_organization()
        return OrderReturn.objects.filter(organization=org)

    @extend_schema(
        summary="Registrar devolución y recuperar stock",
        description="Crea un registro de devolución y actualiza el inventario automáticamente.",
    )
    def create(self, request, *args, **kwargs):
        organization = self.get_organization()
        try:
            order_return = OrderService.process_return(
                organization=organization,
                order_id=request.data.get('order'),
                product_id=request.data.get('product'),
                quantity=int(request.data.get('quantity')),
                reason=request.data.get('reason'),
                notes=request.data.get('notes', ''),
            )

            serializer = self.get_serializer(order_return)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except (DjangoValidationError, ValueError) as e:
            message = e.message if hasattr(e, 'message') else str(e)
            return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)

===================================================================
NEXUS OMS — MVP DEVELOPMENT FEED (PRIORITY 1: SALES & PAYMENTS)
===================================================================
Contexto del Grafo: sales_pipeline.md & payment_pipeline.md
Objetivo: Implementar y estandarizar el registro de pagos en la API REST.

[ ] PASO 1: AGREGAR EL SERIALIZADOR DE PAGOS
    Ruta: src/interfaces/api/serializers.py
    Instrucción: Pega esta clase al final del archivo.

```python
from rest_framework import serializers

class PaymentProcessSerializer(serializers.Serializer):
    """
    Validación de entrada para el procesamiento de pagos desde la API REST.
    Replica las opciones nativas del modelo de datos de pagos.
    """
    method = serializers.ChoiceField(choices=[('CASH', 'Efectivo'), ('CARD', 'Tarjeta')])
    reference = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)
[ ] PASO 2: AGREGAR EL ACTION EN EL VIEWSET DE ÓRDENES
Ruta: src/interfaces/api/views.py
Instrucción:
1. Asegúrate de tener estas importaciones arriba en el archivo:
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from rest_framework.decorators import action
from rest_framework import status
from rest_framework.response import Response
from .serializers import PaymentProcessSerializer
2. Pega este método completo dentro de la clase 'OrderViewSet'.

Python
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
                from src.domain.services.order_service import OrderWorkflowService, workflow_logger
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
[ ] PASO 3: EJECUTAR SUITE DE PRUEBAS

Comando de Terminal:
pytest src/tests/
===================================================================
ESTADO: Esperando ejecución del operador de terminal.
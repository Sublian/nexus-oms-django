===================================================================
NEXUS OMS — MVP DEVELOPMENT FEED (PRIORITY 1: SALES & PAYMENTS)
===================================================================
Contexto del Grafo: sales_pipeline.md & payment_pipeline.md
Objetivo: Estandarizar el registro de pagos desde la API REST.

[x] 1. VISTA ACTUAL (Order ViewSet / Web Views)

### A) OrderViewSet (REST API) — src/interfaces/api/views.py
```python
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
```

### B) order_pay_modal_view (Web Dashboard) — src/interfaces/web/views.py
```python
def order_pay_modal_view(request, org_slug, order_id):
    tenant = get_object_or_404(Organization, slug=org_slug)
    order = get_object_or_404(Order, id=order_id, organization=tenant)

    if OrderStatus.PAID not in Order.VALID_TRANSITIONS.get(order.status, []):
        return HttpResponse('Transición no permitida', status=400)

    if request.method == 'POST':
        # Sanity check: verify stock hasn't gone negative
        for item in order.items.select_related('product'):
            stock = Stock.objects.filter(product=item.product, organization=tenant).first()
            if not stock or stock.quantity < 0:
                return HttpResponse(
                    f'Stock insuficiente para {item.product.name}. Contacta a administración.',
                    status=400
                )

        method = request.POST.get('method', '').strip()
        reference = request.POST.get('reference', '').strip() or None
        fee = (order.total_amount * Decimal('0.035')).quantize(Decimal('0.01')) if method == 'CARD' else Decimal('0.00')

        Payment.objects.get_or_create(
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
        order.status = OrderStatus.PAID

        # Orquestar flujo post-pago ANTES de persistir.
        workflow = OrderWorkflowService(workflow_logger)
        workflow.handle_order_paid(order)

        order.save()
        return _modal_success(request, order, tenant)

    return render(request, 'orders/partials/pay_modal.html', {
        'order': order,
        'tenant': tenant,
        'payment_methods': Payment.PaymentMethod.choices,
    })
```

[x] 2. SERIALIZADOR ACTUAL (Order/Payment Serializers)

### A) OrderItemCreateSerializer — src/interfaces/api/serializers.py
```python
class OrderItemCreateSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)
```

### B) OrderCreateSerializer — src/interfaces/api/serializers.py
```python
class OrderCreateSerializer(serializers.Serializer):
    customer_name = serializers.CharField(max_length=255)
    customer_email = serializers.EmailField()
    items = OrderItemCreateSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Un pedido debe tener al menos un producto.")
        return value
```

### NOTA: No existe PaymentSerializer en API
- Pagos se crean directamente via `Payment.objects.get_or_create()` en order_pay_modal_view
- No hay endpoint REST para crear Payment (solo Web form)
- Payment se registra con: method, amount (=Order.total_amount), fee_amount, transaction_reference

===================================================================
INSTRUCCIÓN AL OPERADOR: No analices, no crees documentación. Extrae los dos fragmentos de código solicitados y agrégalos a este archivo.
===================================================================
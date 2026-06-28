# 🕵️‍♂️ Plan de Investigación Forense: S2.1A.1 — Current Flow Discovery

**Objetivo:** Inspeccionar el repositorio de Nexus OMS para extraer evidencia física y responder el checklist de control de flujos.
**Restricción Estricta:** NO modificar código, NO crear abstracciones, NO sacar conclusiones.

## 📋 Lista de Verificación para el Operador

### 1. Contexto de Identidad
- [x] Determinar la clase exacta en 'DEFAULT_AUTHENTICATION_CLASSES' en settings.
  ```python
  # config/settings/base.py líneas 135-137
  'DEFAULT_AUTHENTICATION_CLASSES': [
      'rest_framework_simplejwt.authentication.JWTAuthentication',
  ],
  ```

- [x] Encontrar la definición física de 'organization_id' en el modelo de usuario personalizado.
  ```python
  # src/domain/models/users.py líneas 39-45
  organization = models.ForeignKey(
      'Organization',
      on_delete=models.CASCADE,
      related_name='users',
      null=True,   # null permite superusers sin organización (admin central)
      blank=True,
  )
  # Django ORM genera automáticamente organization_id como campo en DB
  ```

### 2. Flujo del Pedido (Order ViewSet / Serializer / Model)
- [x] Extraer el código de 'get_queryset()' del ViewSet de Pedidos.
  ```python
  # src/interfaces/api/views.py líneas 91-93
  def get_queryset(self):
      org = self.get_organization()
      return Order.objects.filter(organization=org)
  ```

- [x] Extraer el código de 'perform_create()' o 'create()' del ViewSet de Pedidos.
  ```python
  # src/interfaces/api/views.py líneas 95-126
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

- [x] Verificar si existe la palabra 'organization_id' en los archivos de la app de ventas.
  Contexto: Field `organization` definido en TenantModel (herencia de Order)
  ```python
  # src/infrastructure/models.py líneas 5-10
  class TenantModel(models.Model):
      organization = models.ForeignKey(
          'domain.Organization',
          on_delete=models.CASCADE,
          related_name="%(class)s_items"
      )
  ```
  Django crea automáticamente `organization_id` en base de datos.

- [x] Identificar si el ViewSet usa 'permission_classes' personalizadas.
  No definidas explícitamente en OrderViewSet. Usa default REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'] = IsAuthenticated.
  Hereda de TenantViewMixin que implementa get_organization() para aislamiento por tenant.

### 3. Cobertura Existente
- [x] Buscar archivos con el patrón 'test_*.py' en la aplicación de ventas que apunten a permisos o aislamiento.

  **Tests de aislamiento de tenant:**
  - `src/tests/security/test_tenant_isolation.py` — TestTenantManagerAutoFiltering verifica que TenantManager filtra automáticamente por contexto
  - `src/tests/test_api_endpoints.py` — test_list_orders_only_returns_tenant_data verifica que el endpoint de órdenes retorna solo datos del tenant actual

*Nota para el operador: Rellena los hallazgos con código fuente extraído mediante 'cat' o 'grep'. No interpretes el resultado.*

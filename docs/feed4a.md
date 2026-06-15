
### 🚫 RESTRICCIONES DE ALCANCE INMUTABLES:
PROHIBIDO modificar archivos de UI, HTML, templates, HTMX, Tailwind o vistas del dashboard. PROHIBIDO generar archivos de migración (`makemigrations`) o mutar el esquema físico de la base de datos PostgreSQL.

### 🐛 PASO 0: REPARACIÓN DEL SEEDER DE DESARROLLO (Urgente)
Antes de auditar el modelo, repara el script de desarrollo `src/domain/management/commands/seed_data.py`. 
- En las líneas 269 y 273 (o donde corresponda), se está generando un `TypeError` al intentar sumar tipos `Decimal` y `float` con la variable `order_shipping`.
- Asegura que `order_shipping` sea casteado explícitamente usando `Decimal(str(order_shipping))` antes de sumarse a los totales financieros de la orden.
- Una vez reparado, ejecuta inmediatamente el commit:
  `git commit -am "fix: cast order_shipping to Decimal in seed_data command"`
- Corre el seeder en el contenedor para asegurar que la DB local tenga registros de prueba:
  `docker-compose exec web python manage.py seed_data --orders 100`

### 🔍 PASO 1.0: VERIFICACIÓN FÍSICA DEL MODELO (Obligatorio)
Inspecciona la definición exacta del modelo `ExternalRequestLog` en Django y reporta en esta consola:
1. El tipo de dato exacto de los campos `order` u `order_id` (¿ForeignKey entera, UUIDField o IntegerField?).
2. El tipo de dato exacto de `organization_id`.
3. El estado del campo `service_id` (¿Es una ForeignKey? ¿Es obligatorio `null=False` o acepta `null=True`?).
4. Confirma si existe alguna discrepancia entre el UUID canónico de la orden y la columna física en la base de datos.

### 🔍 PASO 1.1: PRE-CHECK DE FIRMAS DE FACTURACIÓN (Obligatorio)
Inspecciona `src/application/providers/nubefact_client.py` y reporta en consola:
1. Analiza las firmas exactas de los métodos `create_invoice()` y `get_invoice_status()`.
2. Confirma si reciben el objeto `Order` completo, un diccionario, o si tienen acceso directo a los IDs y contextos requeridos para construir el log sin propagar parámetros por múltiples capas del sistema.

⚠️ GUARDRAIL DE DETENCIÓN CONTRACTUAL: Si en el Paso 1.0 o 1.1 detectas que el cliente carece de contexto de la orden, o que los tipos de datos colisionan exigiendo cambiar firmas en Use Cases, Tasks o Services, DETÉN la implementación por completo. No escribas código de producción y reporta la ruta mínima de propagación para la aprobación de arquitectura. Si todo es limpio, procede de inmediato con el Paso 1.2.

### 🚀 PASO 1.2: IMPLEMENTACIÓN DE ENTREGABLES

1. ENTREGABLE A: Instrumentación de `ExternalRequestLog`
   - Modifica `src/application/providers/nubefact_client.py` e inyecta la creación del log capturando la latencia precisa en `duration_ms` tras `requests.post()`.
   - Persiste `ExternalRequestLog.objects.create(...)` respetando los tipos nativos exactos hallados en el Paso 1.0 (mapea `service_id=None` si es nullable y no hay contexto del servicio).
   - REGLA DE ANTIDUPLICACIÓN: El log se registra ÚNICAMENTE dentro de este cliente HTTP.

2. ENTREGABLE B: Taxonomía de Errores Transitoria
   - Crea un Enum puro de Python en el dominio (`TEMPORARY`, `PERMANENT`, `AUTH`, `VALIDATION`, `RATE_LIMIT`) y una función pura `classify_error(exception_or_status_code)`.
   - Estampa la categoría como un prefijo explícito dentro de la columna de texto existente: `error_message = f"[{category}] {str(exception)}"`. (Nota: Esta es una solución de transición temporal para evitar deudas de migración).

3. ENTREGABLE C: QA y Nuevas Pruebas en Docker
   - Desarrolla pruebas unitarias específicas dentro de la suite para verificar de forma real en el contenedor que el log se crea, `duration_ms` se guarda, y la taxonomía traduce los prefijos `[TEMPORARY]` y `[PERMANENT]` correctamente.

### 💾 POLÍTICA DE COMMITS DE GIT (Entregables Coherentes):
Ejecuta un commit en Git por cada hito funcional completo terminado:
- Commit 2: `feat: instrument external request log for nubefact client`
- Commit 3: `feat: implement dynamic error taxonomy parsing`
- Commit 4: `test: add unit tests for observability logs and taxonomy`
- Commit 5: `docs: update project state in resume.md and handoff`

### 🐋 VALIDACIÓN FINAL EN CONTENEDOR:
Valida la suite ejecutando: `docker-compose exec web pytest -v`
Muestra el bloque de texto crudo de los resultados (el número total de tests debe subir de 307 debido a las nuevas pruebas).

Reporta los hallazgos de los Checkpoints 1.0 y 1.1 antes de escribir código.
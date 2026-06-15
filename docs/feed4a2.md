
### 🚫 RESTRICCIONES DE ALCANCE INMUTABLES:
PROHIBIDO modificar archivos de UI, HTML, templates, HTMX o vistas del dashboard. PROHIBIDO generar archivos de migración (`makemigrations`) o mutar el esquema físico de la base de datos PostgreSQL.

### 🐛 PASO 0: REPARACIÓN DEL SEEDER DE DESARROLLO (Urgente)
Antes de hacer cualquier inspección, repara el script de desarrollo `src/domain/management/commands/seed_data.py`. 
- En las líneas 269 y 273 (o correspondientes), se genera un `TypeError` al intentar sumar tipos `Decimal` y `float` con la variable `order_shipping`.
- Asegura que `order_shipping` sea casteado explícitamente usando `Decimal(str(order_shipping))` antes de sumarse a los totales financieros.
- Una vez reparado, ejecuta inmediatamente el commit:
  `git commit -am "fix: cast order_shipping to Decimal in seed_data command"`
- Corre el seeder en el contenedor para asegurar que la DB local tenga registros de prueba:
  `docker-compose exec web python manage.py seed_data --orders 100`

### 🔍 PASO 1.0: VERIFICACIÓN FÍSICA DEL MODELO LOGS
Inspecciona la definición del modelo `ExternalRequestLog` en Django y reporta en esta consola el tipo de dato exacto de los campos `order` (u `order_id`), `organization_id` y `service_id` (confirmando si este último es nullable).

### 🔍 PASO 1.1.B: MINI-DISCOVERY DE SEGURIDAD (Obligatorio)
Inspecciona el método `execute()` en `InvoiceStatusQueryUseCase` y muestra en esta consola:
1. El bloque de código exacto (las líneas literales) de dicho método.
2. Confirma si el objeto `order` completo está instanciado y disponible en el scope local de la llamada a `provider.get_invoice_status`.

### 🔍 PASO 1.1.C: INSPECCIÓN DE LA COLA DE SINCRONIZACIÓN (Crítico para Diseño)
Inspecciona la definición del modelo `InvoiceSyncQueue` (o el componente equivalente que maneje la cola de estados).
1. Muestra sus campos físicos en base de datos o atributos de modelo.
2. Determina y reporta si contiene de forma nativa las columnas/relaciones: `order_id`, `organization_id` y `external_id`.

---

⚠️ GUARDRAIL CONTRACTUAL DE DETENCIÓN:
Muestra toda la evidencia recolectada en la consola. DETÉN toda intención de escritura de código de producción o modificación de firmas hasta que evaluemos los resultados bajo la siguiente matriz:

- Si la evidencia demuestra el ESCENARIO C (`InvoiceSyncQueue` tiene toda la correlación), esperaremos instrucciones para no alterar interfaces.
- Si demuestra el ESCENARIO A (El Use Case tiene el objeto `order` pero la cola no ayuda), evaluaremos modificar la firma de `InvoiceProvider`.
- Si demuestra el ESCENARIO B (No hay objeto `order` ni contexto), la implementación se congela.

Mústrame el código de execute() y los campos de InvoiceSyncQueue para tomar la decisión.

### 🟢 MATRIZ EVALUADA — AUTORIZACIÓN TOTAL PARA PASO 1.2 (ESCENARIO A)

Excelente reporte de evidencia. Arquitectura y Staff Engineering aprueban formalmente el Escenario A. Al estar el objeto `order` disponible en la línea 27 del Use Case, el impacto queda perfectamente acotado. 

Tienes luz verde total para levantar el guardrail de detención y proceder con la codificación de todos los entregables.

### 🚀 INSTRUCCIONES DE EJECUCIÓN (PASO 1.2):

1. CAMBIO DE FIRMA PERIFÉRICO:
   - Modifica la firma de `get_invoice_status` para recibir el objeto de la orden:
     `def get_invoice_status(self, order, external_id: str) -> dict:`
   - Aplica este cambio de firma estrictamente en los 4 puntos identificados: `InvoiceProvider`, `NubefactClient`, `MockNubefactClient` y el punto de llamada en `InvoiceStatusQueryUseCase` (línea 46).

2. ENTREGABLE A: Instrumentación de `ExternalRequestLog`
   - Modifica `src/application/providers/nubefact_client.py`. Encamina las llamadas de `requests.post()` tanto en `create_invoice` como en `get_invoice_status` para medir la latencia exacta en milisegundos (`duration_ms`).
   - Justo después de recibir la respuesta (o capturar la excepción), persiste el log haciendo uso de:
     `ExternalRequestLog.objects.create(...)`
   - Asegúrate de mapear: `provider_name="nubefact"`, `operation`, `request_payload`, `response_payload`, `status_code`, `duration_ms`, `success`, `order_id=order.id` y `organization_id=order.organization_id`. Pasa `service_id=None` ya que es nullable.
   - REGLA DE ANTIDUPLICACIÓN: El log se registra ÚNICAMENTE aquí adentro.

3. ENTREGABLE B: Taxonomía de Errores Transitoria
   - Implementa el Enum con las categorías (`TEMPORARY`, `PERMANENT`, `AUTH`, `VALIDATION`, `RATE_LIMIT`) y la función pura `classify_error()`.
   - Estampa la categoría calculada como un prefijo explícito en la columna de texto existente: `error_message = f"[{category}] {str(exception)}"`.

4. ENTREGABLE C: QA & Nuevas Pruebas en Docker
   - Desarrolla las pruebas unitarias que verifiquen la persistencia de `ExternalRequestLog`, el cálculo de `duration_ms` y los prefijos de la taxonomía.

### 💾 POLÍTICA DE COMMITS COHERENTES (Git):
No acumules código. Ejecuta un commit en Git por cada hito funcional completo terminado:
- Commit 2: `feat: instrument external request log for nubefact client`
- Commit 3: `feat: implement dynamic error taxonomy parsing`
- Commit 4: `test: add unit tests for observability logs and taxonomy`
- Commit 5: `docs: update project state in resume.md and handoff`

### 🐋 VALIDACIÓN FINAL DE LA SUITE:
Corre el comando real del contenedor: `docker-compose exec web pytest -v`
Muéstrame el nuevo conteo total de pruebas en verde (que debe superar las 307 iniciales).

Procede con la implementación del Commit 2.
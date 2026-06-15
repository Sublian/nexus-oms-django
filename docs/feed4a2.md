
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
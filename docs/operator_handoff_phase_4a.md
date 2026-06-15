# 🧭 Operator Handoff — FASE 4A: Observability Foundation

## 1. 🟢 ESTADO REAL DEL PROYECTO
- **Proyecto:** Nexus OMS
- **Baseline de Calidad:** 307 / 307 PASSED (0 failed, 0 errors).
- **Validación de QA Obligatoria:** Verificado en contenedor real mediante:
  `docker-compose exec web pytest -v`
- **Aislamiento de Infraestructura:** El entorno de pruebas está completamente blindado mediante fixtures locales en `src/tests/interfaces/web/conftest.py`. Está terminantemente PROHIBIDO realizar llamadas HTTP externas (ej. `api.migo.pe`) en tiempo de testing.

## 2. 🏛️ DECISIONES ARQUITECTÓNICAS CERRADAS (Inmutables)
- **Diseño de Dominio:** El modelo `Order` es el agregado principal. Queda estrictamente PROHIBIDO crear modelos o agregados alternativos como `Invoice`, `InvoiceEvent` o tablas históricas nuevas.
- **Correlation ID Canónico:** El campo existente `order_id` (UUID nativo) es el identificador único oficial para trazar todo el ciclo transaccional (`Order` -> `InvoiceSyncQueue` -> `ExternalRequestLog` -> `AccountingEntry`). No se permite la creación de `trace_id`, `request_id` o similares.
- **Seguridad (T6 Mitigation):** El control de acceso está activo a nivel de vista. Cualquier petición realizada por un `superuser` sin un contexto explícito de organización (`organization_id` / tenant) debe retornar un `403 Forbidden` o `PermissionDenied`. No alterar este comportamiento.

## 3. 🔍 ESTRUCTURA REAL DE POSTGRESQL (ExternalRequestLog)
La auditoría física de la base de datos confirma que el modelo `ExternalRequestLog` ya existe, está activo (usado parcialmente por WooCommerce) y posee el esquema exacto requerido. Queda estrictamente PROHIBIDO realizar migraciones o renombrar campos.
- **Campos confirmados en DB:**
  * `provider_name` (ej. 'nubefact', 'woocommerce')
  * `operation` (ej. 'create_invoice', 'query_status')
  * `request_payload` (JSONField)
  * `response_payload` (JSONField)
  * `status_code` (Integer)
  * `duration_ms` (Integer)
  * `success` (Boolean)
  * `error_message` (TextField)
  * `order_id` (UUID)
  * `organization_id` (Tenant Multi-tenancy)
  * `service_id`

## 4. 🎯 PRÓXIMO OBJETIVO: FASE 4A — OBSERVABILITY FOUNDATION
Implementar la lógica de persistencia y taxonomía de errores en la capa de Backend, estructurada en dos sub-pasos obligatorios:

### 📍 Paso 0: Micro-Discovery (Obligatorio Antes de Codificar)
Antes de modificar una sola línea de código de producción, inspecciona el sistema y reporta brevemente en la consola:
1. Qué clase cliente/adaptador exacta utiliza hoy el flujo de facturación electrónica (sea mock o real).
2. Cuál es el punto único de salida HTTP dentro de dicho cliente donde se debe inyectar el log.
3. Qué campo o estructura existente (`ExternalRequestLog.error_message`, `InvoiceSyncQueue.last_error`, o `metadata`) se utilizará para persistir el resultado de la taxonomía de errores.

### 📍 Paso 1: Implementación de la Fundación
Una vez identificados los componentes en el Paso 0, procede con la codificación:
- **Entregable A (Logs de Facturación Unificados):** Instrumenta el cliente de facturación identificado para persistir de manera consistente una entrada en `ExternalRequestLog` utilizando exclusivamente sus campos nativos confirmados en la Sección 3.
  * *Regla de Antiduplicación:* El log se instancia exclusivamente dentro del adaptador/cliente que ejecuta el request HTTP externo, JAMÁS en Use Cases, Services o Celery Tasks. Un request HTTP debe equivaler a exactamente una fila en DB.
  * *Multi-tenancy:* Asegura asociar correctamente `organization=order.organization` y `order_id=order.id`.
- **Entregable B (Taxonomía de Errores Dinámica):** Crea un Enum puro de Python (`TEMPORARY`, `PERMANENT`, `AUTH`, `VALIDATION`, `RATE_LIMIT`) y una función utilitaria (`classify_error(exception_or_status_code)`) para tipificar dinámicamente las excepciones de facturación.
  * *Persistencia:* La categoría calculada debe quedar grabada dentro de los campos de texto existentes (`error_message` o `metadata`) formateada de forma clara (ej. `"[TEMPORARY] Timeout after 30 seconds"`). NO crees nuevas columnas ni alteres la base de datos.

## 🚫 RESTRICCIONES DE CONTROL DE ALCANCE:
- NO tocar archivos de UI, templates HTML, bloques de HTMX o estilos Tailwind.
- NO modificar vistas del dashboard ni controladores de visualización.
- NO generar archivos de migración (`makemigrations`) ni alterar el esquema físico de tablas.
- NO actualizar el archivo de `understanding-graph` en esta sesión.
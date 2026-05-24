Continuemos con Sprint 3 Paso 4.

Objetivo inmediato:
cerrar completamente el ciclo operacional async antes de trabajar UI, analytics o contabilidad avanzada.

Contexto arquitectónico importante:

El sistema evolucionó de un CRUD tradicional hacia una plataforma distribuida multi-tenant basada en consistencia eventual.

Flujo actual:

Order
↓
Invoice Creation
↓
External Provider
↓
Sync Queue
↓
Polling
↓
SUNAT status sync

Pero ahora identificamos una nueva capa de dominio crítica:

Accounting / Ledger

El flujo futuro correcto será:

Order
↓
Payment Confirmed
↓
Invoice Submitted
↓
SUNAT Accepted
↓
Accounting Entry Generated
↓
Financial Ledger Updated

Importante:
NO generar asientos contables cuando invoice_status='submitted'.

Los asientos contables deben existir únicamente cuando:
invoice_status='accepted'

porque recién allí el comprobante existe oficialmente ante SUNAT.

---

## PRIORIDAD ACTUAL

Antes de UI o dashboards debemos cerrar:

1. consistencia operacional
2. idempotencia
3. queue lifecycle
4. observabilidad mínima
5. polling resiliente
6. desacoplamiento progresivo de proveedores externos

NO iniciar analytics todavía.
NO iniciar dashboards todavía.
NO iniciar reporting financiero todavía.

---

# SPRINT 3 — PASO 4

Necesitamos conectar correctamente:

create_invoice_task
↓
InvoiceSyncQueue

Requerimientos:

* cuando create_invoice_task termine exitosamente
* y el documento quede en estado submitted
* y exista hash/external_id válido

debe crearse automáticamente la entrada en InvoiceSyncQueue.

---

## Restricciones importantes

1. solo crear queue item si:

invoice_status == 'submitted'

2. evitar duplicados:

* máximo 1 queue item activo por order
* considerar retries/reentradas Celery

3. mantener idempotencia:

* retries no deben crear registros duplicados
* usar get_or_create o constraint equivalente

4. queue item debe heredar correctamente:

* organization
* tenant
* provider metadata necesaria

5. registrar logs estructurados:

* order_id
* tenant_id
* provider
* queue_action
* invoice_status

6. agregar placeholders para métricas futuras:

* queue_created
* queue_duplicate_prevented
* queue_creation_failed

7. NO agregar dashboards todavía

8. NO agregar analytics todavía

Objetivo:
dejar operativo el flujo async completo de polling.

---

# NUEVO REQUERIMIENTO — QUEUE LIFECYCLE

Necesitamos comenzar a modelar estados operacionales de la cola.

La queue no puede vivir eternamente en retries.

Considerar futuros estados:

* pending
* processing
* completed
* failed
* dead_letter
* exhausted

Objetivo:

* evitar retries infinitos
* permitir recuperación manual futura
* soportar alertas operacionales
* preparar métricas reales
* soportar DLQ (dead letter queue)

No implementar sistema complejo todavía.
Solo preparar estructura limpia y extensible.

---

# POSTERIOR A PASO 4

Después de cerrar Paso 4 pasaremos a un mini sprint:
Operational Visibility

Objetivo:
hacer visible el estado operacional mínimo del sistema.

Implementar:

1. Django Admin

* registrar InvoiceSyncQueue
* registrar CompanyInvoiceConfig

Agregar filtros útiles:

* status
* tenant
* provider
* created_at

2. UI mínima operacional

* mostrar invoice_status en order_list
* badge visual por estado
* mostrar external_id
* mostrar invoice_last_error si existe

3. order_detail_modal

Agregar sección “Facturación”:

* invoice_status
* external_id
* hash
* último error
* timestamps relevantes

No iniciar dashboards complejos todavía.

---

# NUEVA DIRECCIÓN ARQUITECTÓNICA

El sistema ya depende de múltiples integraciones externas.

Necesitamos comenzar a desacoplar proveedores externos del dominio OMS.

Preparar fundaciones para un futuro Integration Layer.

Objetivo futuro:
centralizar configuración y credenciales de servicios externos por tenant.

Diseñar de forma extensible para:

* Nubefact
* SUNAT
* email providers
* WhatsApp/API messaging
* payment gateways
* futuros servicios externos

Necesitamos contemplar:

* provider_name
* base_url
* api_key
* api_secret/token
* retries
* timeout
* rate_limit por servicio
* rate_limit por endpoint
* environment (sandbox/prod)
* enabled/disabled
* expiración futura
* rotación futura
* ownership por organization/tenant
* trazabilidad de requests/responses
* logs estructurados
* tiempos de respuesta
* payload enviado/recibido
* estado de integración

Importante:

algunos proveedores reutilizan el mismo endpoint y cambian comportamiento vía payload/action.

NO asumir:

1 endpoint = 1 operación

---

# NUEVA CAPA FUTURA — ACCOUNTING DOMAIN

El sistema ya necesita prepararse para contabilidad.

NO construir un ERP todavía.

Solo preparar fundaciones limpias para:

* AccountingEntry
* AccountingEntryLine
* ChartOfAccounts
* Ledger
* Financial reporting futuro

Regla crítica:

AccountingEntry solo debe generarse cuando:

invoice_status == 'accepted'

Nunca en:

* submitted
* processing
* retrying

Objetivo:

garantizar consistencia financiera y tributaria real.

---

# PRINCIPIO GENERAL

Prioridad actual:

estabilizar el pipeline distribuido async completo antes de construir capas visuales o analíticas.

El sistema ya dejó de ser CRUD tradicional.
Ahora es una plataforma operacional multi-tenant basada en consistencia eventual.

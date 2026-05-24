Nuevo Sprint 3 (REEMPLAZA el anterior)
Sprint 3 — Polling + Synchronization System
Objetivo

Construir un sistema que:

✅ consulte estados automáticamente
✅ sincronice SUNAT/Nubefact
✅ cierre facturas pendientes
✅ detecte errores tardíos
✅ limpie cola automáticamente
✅ sea multi-tenant safe

Componentes NUEVOS
1. InvoiceSyncQueue Model

Nueva tabla:

class InvoiceSyncQueue(TenantModel):

    order = models.ForeignKey(Order)

    status = models.CharField(
        choices=[
            ("pending", "Pending"),
            ("processing", "Processing"),
            ("completed", "Completed"),
            ("failed", "Failed"),
        ]
    )

    attempts = models.IntegerField(default=0)

    next_retry_at = models.DateTimeField()

    last_response = models.JSONField(null=True)

    last_error = models.TextField(null=True)

    resolved_at = models.DateTimeField(null=True)
¿Por qué es importante?

Porque:

❌ NO quieres consultar TODAS las facturas siempre
❌ eso destruiría costos/performance

Entonces:

✅ solo consultas las pendientes

2. SyncInvoiceStatusTask

Nueva task Celery periódica:

@shared_task
def sync_invoice_status_task():

Esta task:

busca invoices pendientes
consulta Nubefact
actualiza estado
reprograma retry
elimina de cola si terminó
3. InvoiceStatusQueryUseCase

Separar lógica de polling.

NO meter lógica HTTP dentro del task.

Arquitectura correcta:

Task
  ↓
UseCase
  ↓
Provider
  ↓
Nubefact
4. Nubefact Status Endpoint

Necesitarás investigar:

consultar comprobante
consultar ticket
consultar estado SUNAT

y modelar respuestas:

ACCEPTED
REJECTED
PROCESSING
OBSERVED
5. Estado REAL del Invoice

Ahora invoice_status debe evolucionar.

Estados actuales
pending
processing
issued
retrying
failed
Estados nuevos correctos
queued
processing
sunat_processing
accepted
observed
rejected
retrying
failed
6. Retry inteligente de polling

NO consultar cada minuto.

Usar exponential backoff:

1 min
5 min
15 min
30 min
1 h
6 h
24 h
7. Cleanup automático

Cuando:

accepted
rejected
observed

→ remover de queue.

8. Métricas REALES

Ahora sí necesitas observabilidad seria.

Métricas mínimas
invoice.sync.pending
invoice.sync.completed
invoice.sync.failed
invoice.sync.retry
invoice.sunat.accepted
invoice.sunat.rejected
invoice.sunat.processing
9. Alertas operativas

SI:

> 100 invoices pending > 24h

→ alerta.

Porque eso ya es incidente operacional.

Recién después → Sprint 4

Ahora sí:

Sprint 4 — Dashboard Operacional

Porque ya tienes datos reales sincronizados.

Aquí sí entra:
Admin UI
ver invoices
estado SUNAT
tenant
retries
errores
timestamps
Reintento manual

Botón:

Reintentar factura
Cola manual
Agregar nuevamente a sync queue
Observabilidad visual

Dashboard:

Pendientes
Aceptadas
Observadas
Fallidas
Sprint 5 — Reporting + Analytics

AHORA sí.

Porque ya tienes:

✅ datos consistentes
✅ estados reales
✅ histórico confiable

Aquí sí:
reportes financieros
métricas por tenant
facturación mensual
analytics
exportaciones
KPIs
Orden FINAL correcto
ROADMAP REORDENADO
✅ Sprint 1
Provider architecture + tenant config

✅ Sprint 2
Async + locking + retry + NubefactClient

🚨 Sprint 3 (NUEVO PRIORITY)
Polling + synchronization engine

🔜 Sprint 4
Operational dashboard + manual retries

🔜 Sprint 5
Reporting + analytics
Lo más importante

Tu sistema ya dejó de ser:

CRUD de pedidos

Ahora estás construyendo:

Sistema distribuido de consistencia eventual

Y el corazón de eso NO es la UI.

Es:

sincronización confiable de estados externos

Ese es el siguiente milestone arquitectónico real.
OBJETIVO DE GUIA6

Transformar Nexus OMS desde:

Sistema funcional

hacia:

Sistema SaaS operable
multi-tenant
resiliente
auditable
monitoreable
comercializable
VISIÓN OBJETIVO

El sistema final debe permitir:

múltiples empresas
múltiples endpoints Nubefact
múltiples workers async
procesamiento desacoplado
resiliencia ante caídas de SUNAT/Nubefact
trazabilidad completa
soporte operativo
retries automáticos
retries manuales
monitoreo de inconsistencias
dashboards operativos
observabilidad real
soporte para crecimiento
PRINCIPIO MÁS IMPORTANTE
NubeFact NO tiene webhooks reales

Esto cambia completamente la arquitectura.

NUEVO PROBLEMA OPERATIVO

Actualmente:

OMS → NubeFact → respuesta inmediata

Pero en producción real ocurrirá:

SUNAT lento
respuestas parciales
timeout
aceptaciones tardías
estados inconsistentes
errores temporales
pérdida de conectividad

Y como NubeFact NO posee callbacks/webhooks:

EL OMS debe convertirse en el responsable de reconciliar estados.

Esto cambia el sistema.

Mucho.

NUEVA ARQUITECTURA NECESARIA
Arquitectura de reconciliación eventual
Order
  ↓
InvoiceTask
  ↓
NubeFact
  ↓
Respuesta parcial o temporal
  ↓
InvoicePendingSync Queue
  ↓
Polling Worker
  ↓
Consulta periódica
  ↓
Estado final reconciliado
NUEVO CONCEPTO: EVENTUAL CONSISTENCY

Antes:

request → response → done

Ahora:

request → pending → polling → reconciled

Esto es muchísimo más cercano a un SaaS real.

NUEVA ENTIDAD CRÍTICA
InvoiceSyncQueue
Propósito

Mantener una cola persistente de facturas pendientes de reconciliación con NubeFact/SUNAT.

MODELO PROPUESTO
class InvoiceSyncQueue(TenantModel):

    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"

    order = models.ForeignKey(Order)

    status = models.CharField(...)

    attempts = models.IntegerField(default=0)

    next_retry_at = models.DateTimeField()

    last_error = models.TextField(null=True)

    last_response = models.JSONField(null=True)

    locked_at = models.DateTimeField(null=True)

    completed_at = models.DateTimeField(null=True)

    created_at = models.DateTimeField(auto_now_add=True)
¿POR QUÉ ESTA COLA ES NECESARIA?

Porque NubeFact:

NO empuja estados
NO notifica cambios
NO tiene callbacks
NO garantiza sincronía inmediata

Entonces:

TU sistema debe hacer reconciliación activa.

NUEVO FLUJO OPERATIVO
ETAPA 1 — Emisión inicial
Order PAID
  ↓
create_invoice_task
  ↓
NubefactClient.create_invoice()
ETAPA 2 — Resultado ambiguo

Escenarios reales:

Caso	Resultado
HTTP 200 + aceptado	finaliza
HTTP 202	pendiente
timeout	incierto
502	incierto
conexión perdida	incierto
SUNAT lento	incierto

Los estados “inciertos” NO deben marcarse failed inmediatamente.

Deben entrar a reconciliación.

ETAPA 3 — Enqueue reconciliation
InvoiceSyncQueue.create(...)
ETAPA 4 — Polling periódico

Nuevo worker Celery:

sync_pending_invoices_task

Corre:

cada 1 min / 5 min
ETAPA 5 — Consulta a NubeFact

Nuevo endpoint:

consult_invoice_status()
ETAPA 6 — Estado final
accepted
rejected
cancelled
failed
NUEVO ESTÁNDAR DE ESTADOS
invoice_status actual

Actualmente:

pending
processing
issued
retrying
failed
NUEVOS ESTADOS NECESARIOS
queued
processing
submitted
accepted
rejected
retrying
failed
sync_pending
sync_processing
cancelled
DIFERENCIA CRÍTICA
issued ≠ accepted

Esto es MUY importante.

issued

Significa:

NubeFact recibió la solicitud
accepted

Significa:

SUNAT aceptó oficialmente el comprobante
SIN ESTA DIFERENCIA:

Tendrías inconsistencias financieras reales.

NUEVA PRIORIDAD ARQUITECTÓNICA
Reconciliación financiera

Este será el núcleo del SaaS.

SPRINT 3 — RECONCILIACIÓN + POLLING
OBJETIVO

Construir sincronización eventual robusta.

TAREAS
1. Crear InvoiceSyncQueue
Requerimientos
tenant-aware
lockable
retryable
auditable
queryable
observable
2. Crear polling task

Archivo:

src/domain/tasks/sync_invoice_status_task.py
Flujo
@shared_task
def sync_pending_invoices_task():

    pending = (
        InvoiceSyncQueue.objects
        .filter(status="pending")
        .filter(next_retry_at__lte=timezone.now())
    )

    for item in pending:
        sync_single_invoice_task.delay(item.id)
3. Crear sync_single_invoice_task

Debe:

lockear fila
evitar doble polling
consultar Nubefact
actualizar estado
liberar cola
reprogramar retries
4. Crear método provider
provider.get_invoice_status(...)
5. Extender InvoiceProvider ABC
@abstractmethod
def get_invoice_status(self, external_id):
    pass
6. Extender MockNubefactClient

Simular:

accepted
rejected
delayed
timeout
7. Extender NubefactClient real

Implementar:

consultar_comprobante()
8. Backoff exponencial REAL

Ejemplo:

Intento	Delay
1	1 min
2	5 min
3	15 min
4	30 min
5	1 hora
9. Estado terminal

Cuando:

accepted
rejected
cancelled

Entonces:

InvoiceSyncQueue.status = completed

Y sale de la cola.

SPRINT 4 — OPERABILIDAD SaaS

Aquí el proyecto deja de ser backend técnico.

Y se convierte en producto.

OBJETIVO

Dar herramientas operativas reales.

1. Dashboard de facturación

Vista por tenant:

emitidas
pendientes
rechazadas
retrying
inconsistentes
2. Retry manual

Botón:

Reprocesar factura

Debe:

crear nueva task
evitar duplicación
generar auditoría
3. Cola de reconciliación

UI administrativa:

InvoiceSyncQueue Admin

Filtros:

tenant
estado
retries
aging
errores
4. Aging monitor

Facturas:

pending > 30 min

Deben generar alertas.

5. Alertas operativas

Canales:

email
Telegram
Slack

Eventos:

retries agotados
SUNAT caída
tenant sin config
polling stuck
cola creciendo
6. Métricas reales
Prometheus / StatsD

Counters:

invoice_created_total
invoice_failed_total
invoice_retry_total
invoice_sync_total
invoice_sync_failed_total

Timers:

invoice_processing_seconds
invoice_sync_duration

Gauges:

invoice_queue_size
invoice_retry_backlog
7. Structured logging real

Formato obligatorio:

[tenant=]
[order_id=]
[invoice_id=]
[task_id=]
[action=]
[status=]
8. Correlation IDs

Cada workflow debe tener:

correlation_id

Esto permitirá reconstruir:

HTTP → task → provider → sync
SPRINT 5 — HARDENING SaaS

Aquí empiezan los problemas reales de escala.

OBJETIVOS
resiliencia
mantenimiento
observabilidad
soporte
costos
1. Rate limiting por tenant

Evitar:

tenant A consume todos los workers
2. Priority queues

Separar:

critical
default
low
sync
3. Dead letter queue

Facturas imposibles de reconciliar.

4. Snapshot de configuración

Problema:

Tenant cambia token mientras task está en cola.

Solución:

invoice_config_snapshot = JSONField()

Persistido al momento de emisión.

5. Circuit breaker

Si Nubefact cae:

OPEN CIRCUIT

Evita saturar workers.

6. Bulk reconciliation

Procesar muchas facturas juntas.

7. Tenant quotas

Planes SaaS:

Básico → 100 facturas
Pro → 5000
Enterprise → ilimitado
8. Billing interno SaaS

Necesitarás:

consumo mensual
facturas emitidas
tenants activos
límites
SPRINT 6 — COMERCIALIZACIÓN

Aquí ya piensas como empresa.

OBJETIVOS
vender
desplegar
soportar
cobrar
1. Onboarding tenant

Wizard:

empresa
RUC
token
endpoint
pruebas
2. Health checks

Validar:

token válido
endpoint activo
SUNAT reachable
3. Self-service config

Tenant administra:

token
endpoint
certificados
branding
4. Auditoría legal

Exportables:

XML
PDF
CDR
logs
5. Backup strategy
DB
facturas
XMLs
PDFs
auditoría
6. Disaster recovery

Escenarios:

Redis down
Celery down
DB down
SUNAT caída
7. SLA internos

Definir:

Métrica	Target
emisión	< 5s
retry	< 15m
reconciliación	< 1h
disponibilidad	99.5%
NUEVAS MÉTRICAS DE ÉXITO

El estándar ahora cambia.

Antes
“el flujo funciona”
Ahora
“el sistema resiste producción”
NUEVAS MÉTRICAS REALES
Nivel 1 — Correctitud
no duplicación
tenant isolation
idempotencia
Nivel 2 — Operabilidad
retries automáticos
reconciliación
observabilidad
auditoría
Nivel 3 — SaaS readiness
onboarding
quotas
métricas
soporte
billing
CONCLUSIÓN FINAL

Tu proyecto ya cruzó una línea importante.

Ya no estás construyendo:

un CRUD Django

Ahora estás construyendo:

un sistema distribuido multi-tenant
orientado a operación financiera

Y eso requiere:

consistencia eventual
resiliencia
observabilidad
tooling operacional
monitoreo
reconciliación
PRIORIDAD ABSOLUTA INMEDIATA
Implementar reconciliación eventual

Porque:

SIN webhooks,
la responsabilidad del estado financiero es completamente tuya.

Ese será el núcleo real del SaaS.
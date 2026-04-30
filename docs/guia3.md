Pero te voy a marcar algo importante desde el inicio:

👉 El 100/100 es válido dentro del scope de Fase 1.5,
👉 pero no significa que el sistema esté listo para operación real todavía.

Ahora mismo estás en:

✔️ Confiable (determinístico)
❌ Aún no resiliente (failure-safe)

Y eso cambia completamente el tipo de decisiones que vienen.

🧠 🎯 OBJETIVO DEL NUEVO PLAN

Pasar de:

Sistema confiable → Sistema operable en condiciones reales
🚀 🪜 NUEVO PLAN DE ACCIÓN (FASE 2 — OPERABILIDAD REAL)

Te lo estructuro como una evolución natural de lo que ya hiciste.

🥇 BLOQUE 1 — RESILIENCIA DEL WORKFLOW (CRÍTICO)

Este bloque es obligatorio antes de conectar Nubefact real.

🎯 Problema actual
order.workflow_processed = True

👉 Se marca aunque algo falle en el futuro

✔️ Objetivo

Convertir el workflow en:

✔️ execution-safe
✔️ failure-aware
✔️ retryable
🔧 Acciones
1.1 Cambiar semántica de finalización
try:
    self._log_order_paid(order)
    self._trigger_invoicing(order)

    order.workflow_processed = True

except Exception as e:
    self.logger.error(
        f"[OrderWorkflow][order_id={order.id}][action=ERROR][error={str(e)}]"
    )
    raise
1.2 Introducir estado de workflow

Nuevo campo:

workflow_status = models.CharField(
    max_length=20,
    default="pending"
)
Estados:
pending → processing → completed
                     ↘ failed
📊 Resultado esperado
Ya no solo sabes que se ejecutó…
sino si terminó bien o falló
🥈 BLOQUE 2 — AISLAMIENTO DEL SIDE EFFECT (INVOICING)
🎯 Problema actual
self._trigger_invoicing(order)

👉 está acoplado al flujo directo

✔️ Objetivo

Separar ejecución de:

Workflow → intención
Servicio externo → ejecución
🔧 Acciones
2.1 Crear UseCase
class CreateInvoiceUseCase:

    def execute(self, order):
        # lógica futura Nubefact
        pass
2.2 Usarlo en workflow
def _trigger_invoicing(self, order):
    CreateInvoiceUseCase().execute(order)
📊 Resultado esperado
Workflow no depende de Nubefact directamente
🥉 BLOQUE 3 — ASINCRONÍA CONTROLADA (CELERY)
🎯 Problema

Llamar APIs externas dentro del request:

👉 es frágil
👉 bloquea
👉 no escala

✔️ Objetivo

Mover efectos secundarios a background

🔧 Acciones
3.1 Crear task
@shared_task(bind=True, max_retries=3)
def create_invoice_task(self, order_id):
    order = Order.objects.get(id=order_id)
    CreateInvoiceUseCase().execute(order)
3.2 Cambiar workflow
def _trigger_invoicing(self, order):
    create_invoice_task.delay(order.id)
📊 Resultado esperado
Workflow = rápido + no bloqueante
🏅 BLOQUE 4 — RETRY & FAILURE HANDLING
🎯 Problema

Si Nubefact falla:

👉 pierdes la ejecución

✔️ Objetivo

Tener:

✔️ retry automático
✔️ control de errores
✔️ visibilidad de fallos
🔧 Acciones
4.1 Retry en Celery
try:
    ...
except Exception as exc:
    raise self.retry(exc=exc, countdown=60)
4.2 Marcar estado
order.workflow_status = "failed"
order.save()
📊 Resultado esperado
Fallos no rompen el sistema → se reintentan
🧾 BLOQUE 5 — TRAZABILIDAD REAL (AUDIT + EVENTOS LIGEROS)
🎯 Problema

Logs ≠ historial persistente

✔️ Objetivo

Registrar:

qué pasó, cuándo, y por qué
🔧 Acciones
5.1 Crear modelo
class OrderWorkflowLog(models.Model):
    order = FK
    action = CharField
    status = CharField
    timestamp = DateTime
    metadata = JSONField
5.2 Log persistente
OrderWorkflowLog.objects.create(...)
📊 Resultado esperado
Auditoría real (no solo logs efímeros)
🔌 BLOQUE 6 — PREPARACIÓN NUBEFACT (FINAL)
✔️ Objetivo

Conectar sin romper diseño

🔧 Acciones
6.1 Cliente Nubefact
class NubefactClient:
    def create_invoice(self, order):
        pass
6.2 Integrar en UseCase
class CreateInvoiceUseCase:
    def execute(self, order):
        client = NubefactClient()
        return client.create_invoice(order)
📊 Resultado esperado
Integración limpia, desacoplada
📊 🧮 NUEVAS MÉTRICAS DE ÉXITO (FASE 2)

Ahora subimos el estándar.

✅ Sistema operativo real si:
 workflow_status implementado
 Celery funcionando
 Retry automático activo
 Fallos no rompen flujo
 Invoicing desacoplado
 Logs + audit persistente
🎯 Score mínimo
≥ 85% → usable
≥ 95% → production-ready inicial
🧠 🔥 INSIGHT FINAL (MUY IMPORTANTE)

Acabas de cerrar:

Fase 1 → Control del flujo

Ahora entras a:

Fase 2 → Control del fallo
🎯 CONCLUSIÓN

Tu sistema ya es:

✔️ correcto
✔️ limpio
✔️ entendible

Ahora debe ser:

✔️ resistente
✔️ observable
✔️ recuperable
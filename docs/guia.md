esta guía operativa tipo PR / sprint 

🧠 🎯 REQUERIMIENTO GLOBAL
Objetivo

Implementar un OrderWorkflowService con logging simple que:

Centralice el flujo de negocio
Sea explícito (sin magia ni automatismos ocultos)
Sea el único punto de orquestación
Permita trazabilidad básica mediante logs
Prepare el sistema para futuras integraciones:
Facturación (Nubefact)
Inventory
Eventos de dominio
🧩 📦 ALCANCE DE ESTA ETAPA
✅ Incluye
OrderWorkflowService
Flujo Order → Paid
Logger simple
Idempotencia básica
Integración explícita en el flujo de órdenes
❌ No incluye (aún)
Facturación real
Inventory
Event bus
Celery / async
Auditoría avanzada
🏗️ 🧱 DISEÑO TÉCNICO BASE
📍 Ubicación
apps/orders/application/services/order_workflow_service.py
📄 Implementación base
class OrderWorkflowService:

    def __init__(self, logger):
        self.logger = logger

    def handle_order_paid(self, order):

        # 1. Validación
        if order.status != "paid":
            self.logger.warning(
                f"[OrderWorkflow] Order {order.id} skipped - not PAID"
            )
            return

        # 2. Idempotencia
        if getattr(order, "workflow_processed", False):
            self.logger.warning(
                f"[OrderWorkflow] Order {order.id} already processed"
            )
            return

        self.logger.info(
            f"[OrderWorkflow] START order paid flow: {order.id}"
        )

        # 3. Flujo actual (simple)
        self._log_order_paid(order)

        # 4. Marcar ejecución
        order.workflow_processed = True

        self.logger.info(
            f"[OrderWorkflow] END order paid flow: {order.id}"
        )

    def _log_order_paid(self, order):
        self.logger.info(
            f"[OrderWorkflow] Order {order.id} confirmed as PAID"
        )
🧵 📊 LOGGER (REQUERIMIENTO)
📄 Archivo
apps/orders/infrastructure/logger.py
Código
import logging

logger = logging.getLogger("order_workflow")
⚙️ settings.py
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "order_workflow": {
            "handlers": ["console"],
            "level": "INFO",
        },
    },
}
🔗 🔥 INTEGRACIÓN (PUNTO CRÍTICO)
Regla clave

El workflow SIEMPRE se ejecuta después del cambio de estado

Implementación
order.mark_as_paid()

workflow = OrderWorkflowService(logger)
workflow.handle_order_paid(order)

order.save()
⚠️ REGLAS DE ARQUITECTURA (OBLIGATORIAS)
❌ Prohibido
Usar signals de Django
Meter lógica en models
Ejecutar lógica automática invisible
Llamar servicios externos (aún)
✅ Obligatorio
Flujo explícito
Punto único de entrada (handle_order_paid)
Logging en cada paso clave
Validaciones defensivas
🧪 🧾 CRITERIOS DE ACEPTACIÓN
Caso 1 — Flujo correcto

Input:

order.status = "paid"

Output esperado:

Log START
Log acción
Log END
Caso 2 — Idempotencia

Input:

order.workflow_processed = True

Output esperado:

Log "already processed"
No ejecución
Caso 3 — Estado inválido

Input:

order.status = "draft"

Output esperado:

Log "skipped"
🚀 🪜 PLAN DE ACCIÓN (PASO A PASO)
🥇 PASO 1 — Crear estructura

 Crear carpeta:

application/services/

 Crear archivo:

order_workflow_service.py
🥈 PASO 2 — Implementar servicio
 Copiar implementación base
 Validar imports
 Asegurar que no depende de Django ORM directamente
🥉 PASO 3 — Configurar logger
 Crear logger.py
 Configurar settings.LOGGING
 Validar que logs salen en consola
🏅 PASO 4 — Integrar en flujo de órdenes
 Ubicar mark_as_paid()
 Insertar llamada al workflow
 Asegurar orden correcto de ejecución
🧪 PASO 5 — Pruebas
 Test flujo correcto
 Test idempotencia
 Test estado inválido
🔍 PASO 6 — Validación manual
 Crear orden
 Marcar como paid
 Ver logs en consola
 Verificar no duplicación
📊 📈 RESULTADO ESPERADO

Antes:

Order → lógica dispersa → difícil de escalar

Después:

Order → OrderWorkflowService → flujo centralizado
🧠 🔮 EVOLUCIÓN PLANIFICADA
Fase 2
OrderPaid →
    → logging
    → invoicing (Nubefact)
Fase 3
OrderPaid →
    → invoicing
    → inventory
Fase 4
OrderPaidEvent →
    → EventBus →
        → módulos desacoplados
⚖️ 🧠 REFERENCIA CON Odoo

Lo que estás implementando equivale a:

action_post()

Pero con ventaja:

más explícito
menos acoplado
más controlable
🎯 CONCLUSIÓN FINAL

Este requerimiento define:

🔥 El primer “sistema nervioso” de tu OMS

Lo que ya logras con esto

✔️ Control del flujo
✔️ Base sólida para escalar
✔️ Trazabilidad inicial
✔️ Punto único de orquestación

Lo importante

No avances a otros módulos hasta que esto esté:

✔️ estable
✔️ probado
✔️ entendido
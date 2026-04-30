FASE 1.5 — HARDENING DEL WORKFLOW
🎯 OBJETIVO GLOBAL

Transformar tu OrderWorkflowService de:

Funcional → Controlado → ❌ Frágil

a:

Funcional → Controlado → ✅ Confiable → Preparado para escalar
🧩 📦 ALCANCE DE ESTA ITERACIÓN
Incluye:
Persistencia real del workflow
Consistencia de estados
Mejora de logs
Tests más realistas
Primer punto de extensión (sin integrar aún)
No incluye:
Nubefact real
Inventory
Event bus
Celery
🚀 🪜 ROADMAP DETALLADO (PASO A PASO)
🥇 PASO 1 — PERSISTENCIA REAL DEL WORKFLOW
🎯 Objetivo

Eliminar el estado volátil:

order.workflow_processed = True  # ❌ actual
✔️ Requerimientos
 Agregar campo en el modelo Order:
workflow_processed = models.BooleanField(default=False)
 Asegurar que:
Se guarda en DB (order.save())
Se respeta en lecturas posteriores
🔍 Validaciones
 Ejecutar workflow → flag = True
 Volver a ejecutar → NO entra al flujo
 Reiniciar app → estado persiste
🧠 Resultado esperado
Idempotencia → real (no simulada)
🥈 PASO 2 — NORMALIZACIÓN DE ESTADOS
🎯 Problema actual
order.status = "PAID" vs "paid"

👉 riesgo silencioso

✔️ Requerimientos
 Crear constantes o enum:
class OrderStatus:
    DRAFT = "draft"
    PAID = "paid"
    PENDING = "pending"
 Reemplazar TODOS los strings hardcodeados
🔍 Validaciones
 No existen strings sueltos en el código
 Tests usan constantes
 Workflow funciona igual
🧠 Resultado esperado
Consistencia total de estados
🥉 PASO 3 — MEJORA DE LOGGING (OBSERVABILIDAD BÁSICA)
🎯 Problema actual

Logs poco estructurados:

[OrderWorkflow] START order paid flow: 42
✔️ Requerimientos
 Estandarizar formato:
[OrderWorkflow][order_id=42][action=START]
 Agregar eventos clave:
START
VALIDATION_FAIL
SKIP_ALREADY_PROCESSED
ACTION_EXECUTED
END
🔍 Validaciones
 Logs son consistentes
 Fácil de filtrar por order_id
 No hay mensajes ambiguos
🧠 Resultado esperado
Sistema observable sin herramientas externas
🏅 PASO 4 — TESTS DE INTEGRACIÓN (MÍNIMO REAL)
🎯 Problema actual

Todo está mockeado:

order = MagicMock()

👉 esto no prueba persistencia real

✔️ Requerimientos
 Crear 1 test usando modelo real Django
 Usar DB de test
 Ejecutar:
order.mark_as_paid()
workflow.handle_order_paid(order)
order.refresh_from_db()
🔍 Validaciones
 workflow_processed persiste
 Segunda ejecución no entra
 Estado correcto
🧠 Resultado esperado
Confianza real en el sistema
🧪 PASO 5 — REFUERZO DE TESTS EXISTENTES
✔️ Mejoras
 Agregar test para:
case insensitive status (si decides soportarlo)
orden sin atributo workflow_processed
 Validar logs estructurados
🔌 PASO 6 — PRIMER PUNTO DE EXTENSIÓN (SIN FEATURE REAL)
🎯 Objetivo

Preparar el sistema para crecer sin romperlo

✔️ Requerimientos

Agregar método:

def _trigger_invoicing(self, order):
    self.logger.info(
        f"[OrderWorkflow][order_id={order.id}][action=INVOICING_TRIGGERED]"
    )
Integración:
self._log_order_paid(order)
self._trigger_invoicing(order)
🔍 Validaciones
 Se ejecuta en flujo correcto
 No rompe tests existentes
 No hay dependencias externas
🧠 Resultado esperado
Workflow preparado para enchufar Nubefact
📊 📈 ENTREGABLES DE ESTA ITERACIÓN

Al finalizar deberías tener:

✔️ Sistema
Workflow persistente
Estados consistentes
Logs estructurados
Extensible sin romper diseño
✔️ Testing
Unit tests sólidos
1 integration test real
Cobertura de casos clave
✔️ Arquitectura
Sin acoplamientos nuevos
Flujo sigue centralizado
Preparado para siguiente fase
🚀 SIGUIENTE ETAPA (LO QUE VIENE DESPUÉS)

Cuando completes esto:

👉 recién aquí avanzas a:

FASE 2 — INTEGRACIÓN FUNCIONAL
Invoicing real (Nubefact)
Async (Celery)
Retry logic
Primer “side-effect” real
🧠 INSIGHT FINAL (CLAVE)

Esta fase es la diferencia entre:

Proyecto que funciona → Proyecto que escala
🎯 REGLA DE ORO

Si no puedes responder:

“¿Este flujo es 100% confiable en producción?”

👉 entonces aún no debes avanzar
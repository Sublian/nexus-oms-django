# Sprint 2 — Diagnóstico de Riesgos y Plan de Acción

## Tabla de Riesgos (actualizada 17 Mayo 2026 — Pasos 1-4 completados)

| ID | Riesgo | Descripción | Estado actual | Solución |
|----|--------|-------------|---------------|----------|
| R1 | **Todo síncrono** | `_trigger_invoicing` bloquea el HTTP request completo | ❌ `handle_order_paid` se llama en la view, sin Celery | Mover a `create_invoice_task.delay(order.id)` en Sprint 2 |
| R2 | **Race condition** | 2 requests simultáneos pasan el check `workflow_processed` sin lock | ✅ RESUELTO — `_claim_workflow_lock()` con `select_for_update()` en `OrderWorkflowService` | `_claim_workflow_lock`: atomic block + lock DB + sync in-memory object |
| R3 | **Duplicación por retry** | `CreateInvoiceUseCase` no verifica `invoice_external_id` antes de ejecutar | ✅ RESUELTO — guardia al inicio de `execute()`: `if order.invoice_external_id: return` | Retorna el `external_id` existente sin crear factura nueva |
| R4 | **Sin idempotency key** | `MockNubefactClient` genera UUID nuevo en cada llamada | ❌ `MOCK-{uuid4()[:8]}` siempre distinto — duplicación silenciosa | `idempotency_key = f"ORDER-{order.id}"` en el payload |
| R5 | **Campos faltantes en Order** | Sin `invoice_attempts` ni `invoice_last_error`, no hay trazabilidad de fallos | ✅ RESUELTO — migration 0009 agrega ambos campos + estados `processing`/`retrying` | Ver migration 0009 |
| R6 | **Factory débil** | `enabled=True` y `enabled=False` devuelven el mismo Mock — lógica ambigua | ⚠️ Funcional hoy, riesgo cuando llegue NubefactClient real | Reemplazar `enabled` por `provider_type = "nubefact" \| "mock"` en Sprint 4 |
| R7 | **Double save** | `order.save()` ocurre dentro del UseCase (línea 52) Y en la view (línea 536) | ⚠️ No rompe nada hoy porque salvan campos distintos, pero es frágil | Consolidar: UseCase solo modifica campos invoice_*, view salva todo al final |

---

## Estado de campos del modelo Order (post migration 0009)

```python
# Workflow
workflow_processed   BooleanField   default=False
workflow_status      CharField      pending | processing | completed | failed

# Invoice
invoice_status       CharField      pending | processing | issued | retrying | failed  ← ampliado
invoice_external_id  CharField      null=True
invoice_attempts     IntegerField   default=0  ← NUEVO
invoice_last_error   TextField      null=True  ← NUEVO
```

---

## Flujo actual (SÍNCRONO — post Paso 2: con lock + idempotencia)

```
HTTP Request
  │
  ├─ order.status = PAID  (en memoria)
  ├─ OrderWorkflowService.handle_order_paid(order)  ← BLOQUEA HTTP
  │    ├─ fast-path check workflow_processed (memoria)
  │    ├─ _claim_workflow_lock()  ← select_for_update (R2 resuelto)
  │    ├─ _trigger_invoicing(order)
  │    │    └─ CreateInvoiceUseCase.execute()  ← guardia invoice_external_id (R3 resuelto)
  │    │         └─ order.save()  ← SAVE #1  (R7)
  │    └─ order.workflow_processed = True
  └─ order.save()  ← SAVE #2
```

## Flujo objetivo (ASYNC — implementado en Paso 3)

```
HTTP Request
  │
  ├─ order.status = PAID
  ├─ OrderWorkflowService.handle_order_paid(order)
  │    └─ create_invoice_task.delay(order.id)  ← encola y libera HTTP
  └─ order.save()

Celery Worker (async)
  ├─ select_for_update() + check invoice_external_id  ← resuelve R2 + R3
  ├─ order.invoice_status = 'processing'
  ├─ order.invoice_attempts += 1
  ├─ CreateInvoiceUseCase.execute()
  └─ order.invoice_status = 'issued' | 'retrying' | 'failed'
     order.invoice_last_error = ...  ← si falla
```

---

## Orden de implementación

```
✅ Paso 1 — Campos en modelo     migration 0009 (invoice_attempts, invoice_last_error, estados ampliados)
✅ Paso 2 — Lock + idempotencia  _claim_workflow_lock() en OrderWorkflowService + guardia en CreateInvoiceUseCase
✅ Paso 3 — Celery task          create_invoice_task: lock, idempotencia, retry, estados processing/retrying/failed
✅ Paso 4 — Exception hierarchy  NubefactPermanentError en UseCase (DoesNotExist) + contrato en InvoiceProvider ABC
🔜 Paso 5 — NubefactClient real  HTTP real + idempotency_key + factory robusta (Sprint 4)
```

---

🧠 1. LO QUE ESTÁ EXCELENTE (DE VERDAD)

Aquí no hay matices, esto está bien diseñado.

🟢 Multi-tenancy + Provider resolution

Esto es lo mejor que hiciste:

Order → CompanyInvoiceConfig → Provider Factory → Client

👉 Esto evita:

contaminación entre tenants
facturación cruzada
bugs silenciosos difíciles de detectar

📌 Esto es arquitectura SaaS correcta.

🟢 UseCase + Provider desacoplado

Separaste:

Workflow → UseCase → Provider

👉 Esto es exactamente lo que permite:

testear sin HTTP
mockear sin fricción
cambiar proveedor sin romper todo
🟢 Auditoría persistente

OrderWorkflowLog:

👉 esto es clave para operación real
👉 logs ≠ auditoría

Esto te da:

trazabilidad histórica
debugging post-mortem
base para analytics futuro
🟢 Métricas + roadmap claros

Tu documento no es solo descriptivo:

👉 es operativo

Eso es raro y valioso.

🟡 2. LO QUE ESTÁ BIEN PERO AÚN NO COMPLETO

Aquí es donde empieza el trabajo serio.

🟡 "Graceful degradation" (ojo con esto)

Dices:

workflow marca COMPLETED incluso si invoicing falla

👉 esto es correcto… pero incompleto

Problema

Te queda esto:

Order:
  status = PAID
  workflow = COMPLETED
  invoice_status = FAILED
Pregunta crítica

👉 ¿quién reintenta esa factura?

Ahora mismo:

❌ nadie
❌ no hay mecanismo automático
❌ depende de intervención manual

🟡 invoice_status es plano

Ahora tienes:

pending | issued | failed

👉 pero te falta granularidad:

retrying
permanent_failed
queued
🟡 Factory basada en enabled

Esto:

if config.enabled:
    NubefactClient

👉 es débil

Mejor diseño
config.provider_type = "nubefact" | "mock"

👉 te evita lógica ambigua después

🔴 3. RIESGOS OCULTOS (LOS IMPORTANTES)

Aquí está el valor real de esta review.

❗ 1. DUPLICACIÓN POR RETRY (CRÍTICO)

Cuando implementes Celery:

retry → vuelve a ejecutar create_invoice
Problema

Si Nubefact ya procesó:

👉 puedes crear doble factura

🔥 Solución obligatoria

Necesitas:

idempotency_key

Ejemplo:

idempotency_key = f"order-{order.id}"

Y enviarlo a Nubefact si lo soporta
(o simularlo tú)

❗ 2. RACE CONDITION

Escenario:

- 2 workers procesan misma orden

Resultado:

❌ doble invoice
❌ inconsistencia

Solución

Locking:

select_for_update()

o:

invoice_status = processing

antes de ejecutar

❗ 3. CONFIG CAMBIANTE EN TIEMPO

Escenario:

- tenant cambia endpoint_url
- task en cola usa config vieja

👉 inconsistencia

Solución

Persistir snapshot:

order.invoice_config_snapshot

(opcional pero pro)

❗ 4. FALTA DE TIMEOUT CONTROLADO

Si Nubefact cuelga:

❌ Celery worker bloqueado

👉 debes definir:

timeout=10-15s

SIEMPRE

🚀 4. AJUSTES PARA SPRINT 2 (CELERY)

Este es el plan refinado, listo para ejecutar.

🥇 Paso 1 — Task segura
@shared_task(bind=True, max_retries=5)
def create_invoice_task(self, order_id):

    order = Order.objects.select_for_update().get(id=order_id)

    if order.invoice_status == "issued":
        return

    order.invoice_status = "processing"
    order.save()

    try:
        CreateInvoiceUseCase().execute(order)

    except NubefactTemporaryError as exc:
        raise self.retry(exc=exc)

    except NubefactPermanentError:
        order.invoice_status = "failed"
        order.save()
🥈 Paso 2 — Idempotencia

En UseCase:

if order.invoice_external_id:
    return
🥉 Paso 3 — Idempotency key
payload["external_id"] = f"ORDER-{order.id}"
🏅 Paso 4 — Factory robusta
if config.provider_type == "mock":
    return MockNubefactClient()

elif config.provider_type == "nubefact":
    return NubefactClient(config)
🎯 5. MÉTRICAS NUEVAS (YA NO 100/100)

Ahora el estándar sube.

Sistema operativo si:
 No hay duplicación con retries
 Celery no bloquea workers
 Fallos son recuperables
 Multi-tenant sigue aislado en async
 Facturación es eventual pero consistente
🧠 CONCLUSIÓN FINAL

Tu estado actual es:

✔️ Arquitectura correcta
✔️ Base sólida
✔️ Diseño SaaS válido

Pero aún no es:

❌ resiliente a concurrencia
❌ protegido contra duplicación
❌ preparado para retry real
🔥 INSIGHT CLAVE

El mayor riesgo de esta fase NO es Nubefact.

Es este:

retry + async + multi-tenant

Si eso falla:

👉 tu sistema factura mal
👉 y eso en producción es crítico

🚀 SIGUIENTE MOVIMIENTO

Te recomiendo:

👉 implementar Sprint 2 con foco en:

locking
idempotencia real
retry controlado

---
# consideraciones

Voy a diseñarte el create_invoice_task como debería existir en un sistema SaaS serio:

✔️ idempotente
✔️ safe ante concurrencia
✔️ retry inteligente
✔️ observable (logs + métricas)
✔️ multi-tenant safe

🧠 🎯 PRINCIPIOS DEL DISEÑO

Este task debe garantizar:

1. Nunca crear doble factura
2. Poder reintentarse sin efectos secundarios
3. No bloquear workers
4. Ser trazable completamente
5. Aislar correctamente el tenant
🏗️ 📦 DEPENDENCIAS NECESARIAS

Antes del task necesitas:

Campos en Order
invoice_status = models.CharField(...)
invoice_external_id = models.CharField(...)
invoice_attempts = models.IntegerField(default=0)
invoice_last_error = models.TextField(null=True)
Estados recomendados
pending
processing
issued
failed
retrying
Excepciones
class NubefactTemporaryError(Exception):
    pass

class NubefactPermanentError(Exception):
    pass
🚀 🧱 TASK — IMPLEMENTACIÓN COMPLETA
from celery import shared_task
from django.db import transaction
from django.utils import timezone

from src.domain.models import Order
from src.application.usecases.create_invoice import CreateInvoiceUseCase
from src.domain.exceptions import (
    NubefactTemporaryError,
    NubefactPermanentError
)
import logging

logger = logging.getLogger("invoice_task")


@shared_task(
    bind=True,
    max_retries=5,
    autoretry_for=(),  # control manual
    retry_backoff=True,
    retry_backoff_max=600,  # max 10 min
)
def create_invoice_task(self, order_id: int):

    task_id = self.request.id

    logger.info(
        f"[InvoiceTask][task_id={task_id}][order_id={order_id}][action=START]"
    )

    try:

        # 🔒 BLOQUE CRÍTICO — LOCK DB
        with transaction.atomic():

            order = (
                Order.objects
                .select_for_update()
                .get(id=order_id)
            )

            # 🧠 IDPOTENCIA FUERTE
            if order.invoice_external_id:
                logger.info(
                    f"[InvoiceTask][task_id={task_id}][order_id={order.id}]"
                    f"[action=SKIP_ALREADY_ISSUED]"
                )
                return

            # 🚫 evitar doble procesamiento concurrente
            if order.invoice_status == "processing":
                logger.warning(
                    f"[InvoiceTask][task_id={task_id}][order_id={order.id}]"
                    f"[action=SKIP_ALREADY_PROCESSING]"
                )
                return

            # 🏁 marcar inicio
            order.invoice_status = "processing"
            order.invoice_attempts += 1
            order.save()

        # 🚀 EJECUCIÓN FUERA DEL LOCK
        usecase = CreateInvoiceUseCase()

        result = usecase.execute(order)

        # 🔒 persistencia final
        with transaction.atomic():

            order = Order.objects.select_for_update().get(id=order_id)

            order.invoice_status = "issued"
            order.invoice_external_id = result.get("external_id")
            order.invoice_last_error = None
            order.save()

        logger.info(
            f"[InvoiceTask][task_id={task_id}][order_id={order.id}]"
            f"[action=SUCCESS][external_id={order.invoice_external_id}]"
        )

        # 📊 MÉTRICA (placeholder)
        # metrics.increment("invoice.success")

        return result

    # 🔁 ERRORES TEMPORALES (retry)
    except NubefactTemporaryError as exc:

        logger.warning(
            f"[InvoiceTask][task_id={task_id}][order_id={order_id}]"
            f"[action=RETRY][error={str(exc)}][retry={self.request.retries}]"
        )

        try:
            order = Order.objects.get(id=order_id)
            order.invoice_status = "retrying"
            order.invoice_last_error = str(exc)
            order.save()
        except Exception:
            pass

        # 📊 MÉTRICA
        # metrics.increment("invoice.retry")

        raise self.retry(exc=exc)

    # ❌ ERRORES PERMANENTES
    except NubefactPermanentError as exc:

        logger.error(
            f"[InvoiceTask][task_id={task_id}][order_id={order_id}]"
            f"[action=FAILED_PERMANENT][error={str(exc)}]"
        )

        try:
            order = Order.objects.get(id=order_id)
            order.invoice_status = "failed"
            order.invoice_last_error = str(exc)
            order.save()
        except Exception:
            pass

        # 📊 MÉTRICA
        # metrics.increment("invoice.failed")

        return

    # 🔥 ERRORES INESPERADOS
    except Exception as exc:

        logger.exception(
            f"[InvoiceTask][task_id={task_id}][order_id={order_id}]"
            f"[action=FAILED_UNKNOWN]"
        )

        try:
            order = Order.objects.get(id=order_id)
            order.invoice_status = "failed"
            order.invoice_last_error = str(exc)
            order.save()
        except Exception:
            pass

        raise
🔒 🧠 DECISIONES CLAVE EXPLICADAS
1. select_for_update()
Evita:
- doble ejecución concurrente
- race conditions
2. Doble chequeo de idempotencia
if order.invoice_external_id:

👉 evita duplicación incluso con retries

3. Lock corto
LOCK → marcar estado → liberar

NO ejecutas Nubefact dentro del lock
👉 evita bloquear DB

4. Retry manual (no automático)
autoretry_for=()

👉 controlas tú:

qué se reintenta
qué no
5. Estados intermedios
processing
retrying
failed

👉 esto es clave para debugging

📊 📈 MÉTRICAS RECOMENDADAS

Integra luego con Prometheus / StatsD:

Counters
invoice.success
invoice.failed
invoice.retry
invoice.started
Timers
invoice.execution_time
🧪 TESTS CRÍTICOS (DEBES TENER)
1. Idempotencia
task(order_id)
task(order_id)

👉 1 sola factura

2. Retry

Simular:

raise NubefactTemporaryError

👉 se reintenta

3. Permanent failure
raise NubefactPermanentError

👉 NO retry

4. Concurrencia

Simular:

2 tasks simultáneos

👉 solo uno procesa

⚠️ ERRORES QUE ESTE DISEÑO EVITA
❌ doble facturación

resuelto con:

external_id + lock + idempotencia
❌ worker bloqueado

resuelto con:

no HTTP dentro de lock
❌ retry infinito

resuelto con:

max_retries + clasificación de errores
❌ fuga entre tenants

resuelto porque:

UseCase resuelve config por order.company
🎯 RESULTADO FINAL

Con este task tienes:

✔️ procesamiento async seguro
✔️ idempotencia real
✔️ resiliencia ante fallos
✔️ trazabilidad completa
✔️ preparado para Nubefact real
🧠 INSIGHT FINAL

Este componente (task) es:

🔥 el punto donde tu sistema deja de ser CRUD
🔥 y se convierte en sistema distribuido real

🚀 SIGUIENTE PASO NATURAL

Después de esto:

👉 conectar NubefactClient real
👉 agregar idempotency_key en payload
👉 observabilidad con métricas reales
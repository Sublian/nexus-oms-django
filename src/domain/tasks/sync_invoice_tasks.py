"""
Sprint 3 — Polling + Reconciliation Engine

Flujo:
  sync_pending_invoices_task  (Beat, cada 1 min)
    └── sync_single_invoice_task.delay(entry_id)  x N

Garantias:
  - Locking DB en Phase 1 (select_for_update): evita doble polling entre workers
  - Idempotencia: estados terminales y locks frescos son skipeados silenciosamente
  - Lock release en finally: correcto incluso si el UseCase lanza excepcion
  - Backoff exponencial: next_retry_at calculado en InvoiceSyncQueue.schedule_next_retry()
  - Sin logica de negocio SUNAT en el task: toda en InvoiceStatusQueryUseCase

Separacion estricta: Task -> UseCase -> Provider -> HTTP Client
"""
import logging
from celery import shared_task
from django.db import transaction
from django.utils import timezone

from src.domain.exceptions import NubefactTemporaryError, NubefactPermanentError
from src.application.usecases.query_invoice_status import InvoiceStatusQueryUseCase

logger = logging.getLogger("invoice_sync")

STALE_LOCK_MINUTES = 10
_TERMINAL_STATUSES = frozenset({'accepted', 'observed', 'rejected', 'cancelled'})


# ── Observabilidad ────────────────────────────────────────────────────────────

def _metric(name: str, **tags):
    """
    Placeholder de metrica — wirable a Prometheus/StatsD/DataDog en Sprint 5.
    Metricas disponibles:
      invoice.poll.started        — consulta iniciada
      invoice.poll.success        — estado terminal alcanzado
      invoice.poll.retry          — SUNAT aun procesando, se reagenda
      invoice.poll.failed         — error permanente, sale de cola
      invoice.poll.rate_limited   — throttle por tenant (Sprint 5)
    """
    tag_str = " ".join(f"{k}={v}" for k, v in tags.items())
    logger.info(f"[metric:{name}] {tag_str}")


# ── Fan-out task ──────────────────────────────────────────────────────────────

@shared_task(bind=True, name="tasks.sync_pending_invoices")
def sync_pending_invoices_task(self):
    """
    Barre todas las entradas pendientes y despacha una task por cada una.
    Usa all_objects para operar sobre TODOS los tenants (sin filtro de thread-local).
    """
    from src.domain.models import InvoiceSyncQueue

    now = timezone.now()
    entry_ids = list(
        InvoiceSyncQueue.all_objects
        .filter(status=InvoiceSyncQueue.STATUS_PENDING, next_retry_at__lte=now)
        .values_list('id', flat=True)
    )

    for entry_id in entry_ids:
        sync_single_invoice_task.delay(entry_id)

    logger.info(
        f"[invoice.poll.sweep][task_id={self.request.id}]"
        f"[dispatched={len(entry_ids)}]"
    )
    return len(entry_ids)


# ── Per-entry task ────────────────────────────────────────────────────────────

@shared_task(bind=True, name="tasks.sync_single_invoice", max_retries=0)
def sync_single_invoice_task(self, entry_id: int):
    """
    Consulta el estado de una factura en Nubefact/SUNAT.

    Phase 1 (atomic/corta): adquiere lock, verifica idempotencia, incrementa attempts.
    Phase 2 (fuera del lock): llama UseCase, actualiza cola.
    Finally: libera locked_at siempre, incluso si Phase 2 falla.
    """
    from src.domain.models import InvoiceSyncQueue

    task_id = self.request.id or "eager"

    # ── Phase 1: Lock + idempotencia ─────────────────────────────────────────
    try:
        with transaction.atomic():
            try:
                entry = (
                    InvoiceSyncQueue.all_objects
                    .select_for_update()
                    .select_related('order')
                    .get(id=entry_id)
                )
            except InvoiceSyncQueue.DoesNotExist:
                logger.warning(
                    f"[invoice.poll.not_found][task_id={task_id}][entry_id={entry_id}]"
                )
                return

            # Idempotencia: estado terminal → skip silencioso
            if entry.status in (
                InvoiceSyncQueue.STATUS_COMPLETED,
                InvoiceSyncQueue.STATUS_FAILED,
            ):
                logger.info(
                    f"[invoice.poll.skip][task_id={task_id}]"
                    f"[tenant_id={entry.organization_id}][order_id={entry.order_id}]"
                    f"[reason=terminal_state][status={entry.status}]"
                )
                return

            # Lock fresco → otro worker esta procesando esta entrada
            if entry.locked_at is not None:
                stale_cutoff = timezone.now() - timezone.timedelta(minutes=STALE_LOCK_MINUTES)
                if entry.locked_at > stale_cutoff:
                    logger.info(
                        f"[invoice.poll.skip][task_id={task_id}]"
                        f"[tenant_id={entry.organization_id}][order_id={entry.order_id}]"
                        f"[reason=locked_fresh][locked_at={entry.locked_at}]"
                    )
                    return

            # Adquirir lock + incrementar attempts (persistido atomicamente)
            entry.locked_at = timezone.now()
            entry.status = InvoiceSyncQueue.STATUS_PROCESSING
            entry.attempts += 1
            entry.save(update_fields=["locked_at", "status", "attempts"])

    except Exception as exc:
        logger.error(
            f"[invoice.poll.lock_failed][task_id={task_id}]"
            f"[entry_id={entry_id}][error={exc}]"
        )
        raise

    # Capturar identificadores antes de salir del scope del atomic
    order_id   = entry.order_id
    org_id     = entry.organization_id
    external_id = entry.order.invoice_external_id

    _metric(
        "invoice.poll.started",
        task_id=task_id, tenant_id=org_id,
        order_id=order_id, external_id=external_id,
    )
    logger.info(
        f"[invoice.poll.started][task_id={task_id}]"
        f"[tenant_id={org_id}][order_id={order_id}]"
        f"[external_id={external_id}][attempt={entry.attempts}]"
    )

    # ── Phase 2: Consulta UseCase (fuera del lock) ────────────────────────────
    try:
        result = InvoiceStatusQueryUseCase().execute(entry)

        order_status = entry.order.invoice_status  # actualizado por el UseCase

        if order_status in _TERMINAL_STATUSES:
            entry.mark_completed()
            entry.last_response = result.get("raw_response")
            entry.save(update_fields=["status", "last_response", "completed_at"])

            _metric(
                "invoice.poll.success",
                task_id=task_id, tenant_id=org_id,
                order_id=order_id, status=order_status,
            )
            logger.info(
                f"[invoice.poll.success][task_id={task_id}]"
                f"[tenant_id={org_id}][order_id={order_id}][status={order_status}]"
            )

        else:
            # SUNAT aun procesando — reagendar con backoff
            entry.status = InvoiceSyncQueue.STATUS_PENDING
            entry.schedule_next_retry()
            entry.last_response = result.get("raw_response")
            entry.save(update_fields=["status", "next_retry_at", "last_response"])

            _metric(
                "invoice.poll.retry",
                task_id=task_id, tenant_id=org_id,
                order_id=order_id, attempt=entry.attempts,
            )
            logger.info(
                f"[invoice.poll.retry][task_id={task_id}]"
                f"[tenant_id={org_id}][order_id={order_id}]"
                f"[next_retry_at={entry.next_retry_at}][attempt={entry.attempts}]"
            )

    except NubefactTemporaryError as exc:
        # Timeout / 5xx — reagendar con backoff, no marcar como failed
        entry.status = InvoiceSyncQueue.STATUS_PENDING
        entry.schedule_next_retry()
        entry.last_error = str(exc)[:500]
        entry.save(update_fields=["status", "next_retry_at", "last_error"])

        _metric(
            "invoice.poll.retry",
            task_id=task_id, tenant_id=org_id,
            order_id=order_id, reason="temporary_error",
        )
        logger.warning(
            f"[invoice.poll.temporary_error][task_id={task_id}]"
            f"[tenant_id={org_id}][order_id={order_id}]"
            f"[error={str(exc)[:300]}]"
        )

    except NubefactPermanentError as exc:
        # 4xx / sin config / sin external_id — fallo definitivo
        entry.mark_failed(str(exc))
        entry.save(update_fields=["status", "last_error", "completed_at"])

        _metric(
            "invoice.poll.failed",
            task_id=task_id, tenant_id=org_id,
            order_id=order_id, reason="permanent_error",
        )
        logger.error(
            f"[invoice.poll.failed][task_id={task_id}]"
            f"[tenant_id={org_id}][order_id={order_id}]"
            f"[error={str(exc)[:300]}]"
        )

    except Exception as exc:
        # Error inesperado — marcar failed y re-raise para que Celery lo registre
        entry.mark_failed(str(exc))
        entry.save(update_fields=["status", "last_error", "completed_at"])

        _metric(
            "invoice.poll.failed",
            task_id=task_id, tenant_id=org_id,
            order_id=order_id, reason="unexpected",
        )
        logger.exception(
            f"[invoice.poll.unexpected][task_id={task_id}]"
            f"[tenant_id={org_id}][order_id={order_id}]"
        )
        raise

    finally:
        # Liberar locked_at siempre — incluso si Phase 2 lanza excepcion no capturada.
        # Usa .update() directo para no pisar el status ya guardado.
        try:
            InvoiceSyncQueue.all_objects.filter(id=entry_id).update(locked_at=None)
        except Exception as lock_exc:
            logger.error(
                f"[invoice.poll.lock_release_failed]"
                f"[task_id={task_id}][entry_id={entry_id}][error={lock_exc}]"
            )

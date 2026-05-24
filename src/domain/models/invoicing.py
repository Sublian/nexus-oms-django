from django.db import models
from django.utils import timezone

from src.infrastructure.models import TenantModel


BACKOFF_DELAYS_SECONDS = [60, 300, 900, 1800, 3600, 21600, 86400]

MAX_ATTEMPTS = len(BACKOFF_DELAYS_SECONDS)   # 7 — más allá de esto → exhausted


class InvoiceSyncQueue(TenantModel):
    """
    Cola persistente de facturas pendientes de reconciliacion con Nubefact/SUNAT.

    Ciclo de vida:
      pending → processing → completed  (aceptada/observada/rechazada por SUNAT)
                           → failed     (error permanente de proveedor)
                           → exhausted  (MAX_ATTEMPTS alcanzado sin resolución)
                           → dead_letter (intervención manual requerida)

    next_retry_at  — backoff exponencial entre consultas
    locked_at      — previene procesamiento doble entre workers Celery
    last_attempt_at — timestamp de la última consulta efectiva
    exhausted_at   — timestamp cuando se agotaron los reintentos
    """

    STATUS_PENDING     = "pending"
    STATUS_PROCESSING  = "processing"
    STATUS_COMPLETED   = "completed"
    STATUS_FAILED      = "failed"
    STATUS_DEAD_LETTER = "dead_letter"
    STATUS_EXHAUSTED   = "exhausted"

    STATUS_CHOICES = [
        (STATUS_PENDING,     "Pendiente"),
        (STATUS_PROCESSING,  "Procesando"),
        (STATUS_COMPLETED,   "Completada"),
        (STATUS_FAILED,      "Fallida"),
        (STATUS_DEAD_LETTER, "Dead Letter"),
        (STATUS_EXHAUSTED,   "Reintentos Agotados"),
    ]

    RETRYABLE_STATUSES = frozenset({STATUS_FAILED, STATUS_EXHAUSTED, STATUS_DEAD_LETTER})

    order = models.OneToOneField(
        "domain.Order",
        on_delete=models.CASCADE,
        related_name="sync_queue_entry",
        help_text="Orden cuya factura esta pendiente de sincronizacion con SUNAT",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    attempts = models.IntegerField(
        default=0,
        help_text="Numero de consultas realizadas a Nubefact",
    )
    next_retry_at = models.DateTimeField(
        help_text="Proxima ventana de consulta — backoff exponencial",
    )
    last_response = models.JSONField(
        null=True,
        blank=True,
        help_text="Ultima respuesta JSON de Nubefact (para debug y auditoria)",
    )
    last_error = models.TextField(
        null=True,
        blank=True,
        help_text="Ultimo mensaje de error recibido",
    )
    locked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp del lock activo — null si no esta siendo procesada",
    )
    last_attempt_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp de la ultima consulta efectiva a Nubefact",
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp en que alcanzo estado terminal (accepted/rejected/cancelled)",
    )
    exhausted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp en que se agotaron los reintentos (MAX_ATTEMPTS alcanzado)",
    )
    processing_duration_ms = models.IntegerField(
        null=True,
        blank=True,
        help_text="Duracion de la ultima consulta a Nubefact en ms — placeholder para Sprint 5",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cola de Sincronizacion de Factura"
        verbose_name_plural = "Cola de Sincronizacion de Facturas"
        indexes = [
            models.Index(fields=["status", "next_retry_at"]),
            models.Index(fields=["organization", "status"]),
        ]

    def __str__(self):
        return f"SyncQueue order_id={self.order_id} [{self.status}] attempts={self.attempts}"

    # ── Lifecycle helpers ─────────────────────────────────────────────────────

    def schedule_next_retry(self):
        """Calcula next_retry_at con backoff exponencial basado en attempts."""
        idx = min(self.attempts, len(BACKOFF_DELAYS_SECONDS) - 1)
        delay = BACKOFF_DELAYS_SECONDS[idx]
        self.next_retry_at = timezone.now() + timezone.timedelta(seconds=delay)

    def should_exhaust(self) -> bool:
        """True cuando se alcanzó el límite de reintentos."""
        return self.attempts >= MAX_ATTEMPTS

    def mark_completed(self):
        self.status = self.STATUS_COMPLETED
        self.completed_at = timezone.now()

    def mark_failed(self, error: str):
        self.status = self.STATUS_FAILED
        self.last_error = error[:500]
        self.completed_at = timezone.now()

    def mark_exhausted(self, error: str = ""):
        self.status = self.STATUS_EXHAUSTED
        self.exhausted_at = timezone.now()
        self.completed_at = timezone.now()
        if error:
            self.last_error = error[:500]

    def requeue(self):
        """
        Reencola manualmente una entrada en estado terminal de fallo.
        Solo válido para: failed, exhausted, dead_letter.
        next_retry_at = now() → procesada en el próximo sweep (60s).
        """
        if self.status not in self.RETRYABLE_STATUSES:
            raise ValueError(
                f"Cannot requeue entry in status '{self.status}'. "
                f"Allowed: {self.RETRYABLE_STATUSES}"
            )
        self.status = self.STATUS_PENDING
        self.locked_at = None
        self.exhausted_at = None
        self.last_error = None
        self.next_retry_at = timezone.now()

    def release_lock(self):
        self.locked_at = None

# Auditoría persistente del workflow. No son logs efímeros — son hechos históricos.

from django.db import models
from src.infrastructure.models import TenantModel


class OrderWorkflowLog(TenantModel):
    # Acciones posibles en el workflow
    ACTION_CHOICES = [
        ('start', 'Inicio'),
        ('action_executed', 'Acción ejecutada'),
        ('invoicing_triggered', 'Facturación disparada'),
        ('error', 'Error'),
        ('completed', 'Completado'),
        ('skipped_already_processed', 'Saltado: ya procesado'),
        ('skipped_invalid_status', 'Saltado: estado inválido'),
    ]

    order = models.ForeignKey(
        'domain.Order',
        on_delete=models.CASCADE,
        related_name='workflow_logs',
        help_text='Orden asociada'
    )
    action = models.CharField(
        max_length=30,
        choices=ACTION_CHOICES,
        help_text='Acción del workflow'
    )
    status = models.CharField(
        max_length=20,
        default='pending',
        help_text='Estado en momento del evento'
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text='Cuándo ocurrió'
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text='Datos contextuales (error, retry_count, etc)'
    )

    class Meta:
        verbose_name = 'Workflow Log'
        verbose_name_plural = 'Workflow Logs'
        ordering = ['-timestamp']

    def __str__(self):
        return f"Order {self.order.id} - {self.action} @ {self.timestamp}"

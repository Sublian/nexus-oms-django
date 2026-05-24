from django.db import models

from src.infrastructure.models import TenantModel


class ExternalServiceConfig(TenantModel):
    """
    Configuración de un servicio externo por tenant y entorno.

    Diseñado para centralizar credenciales y parámetros de todos los proveedores
    externos: Nubefact, SUNAT, email, WhatsApp, payment gateways, etc.

    Importante: algunos proveedores reutilizan el mismo endpoint base y
    cambian comportamiento vía payload/action. No hay relación 1:1 entre
    ExternalServiceConfig y operación — la operación se especifica en
    ExternalRequestLog.operation.

    unique_together (organization, provider_name, environment) garantiza
    que cada tenant tenga máximo una config por proveedor por entorno.
    """

    class Environment(models.TextChoices):
        SANDBOX    = 'sandbox',    'Sandbox'
        PRODUCTION = 'production', 'Producción'

    provider_name = models.CharField(
        max_length=50,
        help_text='Identificador del proveedor (nubefact | sunat | email | whatsapp | payment_gateway)',
    )
    environment = models.CharField(
        max_length=20,
        choices=Environment.choices,
        default=Environment.SANDBOX,
    )
    base_url = models.URLField(
        help_text='URL base del servicio — las operaciones pueden usar subpaths o payload/action',
    )
    api_key = models.CharField(
        max_length=512,
        help_text='Token / API key principal del servicio',
    )
    api_secret = models.CharField(
        max_length=512,
        blank=True,
        default='',
        help_text='Secret secundario si el proveedor usa autenticación de dos partes',
    )
    timeout_seconds = models.IntegerField(
        default=15,
        help_text='Timeout en segundos para requests a este servicio',
    )
    max_retries = models.IntegerField(
        default=3,
        help_text='Máximo de reintentos ante errores temporales',
    )
    rate_limit_per_minute = models.IntegerField(
        null=True,
        blank=True,
        help_text='Límite de requests por minuto — null si no aplica o no conocido',
    )
    enabled = models.BooleanField(
        default=True,
        help_text='Si False, el sistema no intentará usar este proveedor',
    )
    notes = models.TextField(
        blank=True,
        default='',
        help_text='Notas operacionales (contacto soporte, restricciones, fechas de rotación, etc.)',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Configuración de Servicio Externo'
        verbose_name_plural = 'Configuraciones de Servicios Externos'
        unique_together = [('organization', 'provider_name', 'environment')]
        indexes = [
            models.Index(fields=['organization', 'provider_name']),
        ]

    def __str__(self):
        return f"{self.organization} | {self.provider_name} [{self.environment}]"


class ExternalRequestLog(TenantModel):
    """
    Log de auditoría de cada request a un servicio externo.

    Captura payload, respuesta, duración y resultado para:
    - debugging operacional
    - auditoría regulatoria
    - detección de anomalías futuras (Sprint 5)
    - trazabilidad HTTP ↔ task ↔ provider

    No indexar request_payload/response_payload — solo para consulta puntual.
    Indexar por created_at, provider_name, order para queries operacionales.
    """

    service = models.ForeignKey(
        ExternalServiceConfig,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='request_logs',
        help_text='Config del servicio usado — SET_NULL para preservar logs si config es eliminada',
    )
    provider_name = models.CharField(
        max_length=50,
        help_text='Denormalizado de service.provider_name — persiste aunque la config sea eliminada',
    )
    operation = models.CharField(
        max_length=100,
        help_text='Operación lógica realizada (create_invoice | query_status | send_email, etc.)',
    )
    order = models.ForeignKey(
        'domain.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='external_request_logs',
        help_text='Orden asociada al request — null para operaciones no relacionadas con órdenes',
    )
    request_payload = models.JSONField(
        null=True,
        blank=True,
        help_text='Payload enviado al servicio externo (sanitizado — sin tokens ni PII sensible)',
    )
    response_payload = models.JSONField(
        null=True,
        blank=True,
        help_text='Respuesta recibida del servicio externo (completa para auditoría)',
    )
    status_code = models.IntegerField(
        null=True,
        blank=True,
        help_text='HTTP status code de la respuesta',
    )
    duration_ms = models.IntegerField(
        null=True,
        blank=True,
        help_text='Duración del request en milisegundos',
    )
    success = models.BooleanField(
        null=True,
        help_text='True si el request fue procesado exitosamente por el proveedor',
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text='Mensaje de error si success=False',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Log de Request Externo'
        verbose_name_plural = 'Logs de Requests Externos'
        indexes = [
            models.Index(fields=['organization', 'provider_name', 'created_at']),
            models.Index(fields=['organization', 'operation', 'created_at']),
            models.Index(fields=['order', 'provider_name']),
        ]

    def __str__(self):
        return (
            f"[{self.provider_name}][{self.operation}] "
            f"order_id={self.order_id} status={self.status_code} "
            f"{'OK' if self.success else 'ERR'}"
        )

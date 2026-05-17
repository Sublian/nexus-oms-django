# UseCase: Crear factura desde orden pagada.
# Resuelve dinámicamente: tenant → config → provider → execute
# Punto crítico: evitar contaminación entre tenants

from src.domain.models import CompanyInvoiceConfig
from src.application.providers.factory import get_invoice_provider


class CreateInvoiceUseCase:
    # Sprint 1: Resolver config y provider dinámicamente
    # Fase 2.5: NubefactClient será usado automáticamente si enabled=True

    def __init__(self, provider=None):
        # provider: inyectable para testing (override factory)
        self.provider = provider

    def execute(self, order):
        # Idempotencia: si ya existe un external_id, la factura fue emitida — no duplicar
        if order.invoice_external_id:
            return {
                'status': order.invoice_status,
                'external_id': order.invoice_external_id,
                'error': None,
            }

        # Si provider está inyectado, usarlo directamente (tests unitarios)
        if self.provider is not None:
            result = self.provider.create_invoice(order)
            # Persistir solo si order tiene save method (no mock)
            if hasattr(order, 'save') and callable(order.save):
                order.invoice_status = result['status']
                order.invoice_external_id = result.get('external_id')
                order.save()
            return result

        # Provider no inyectado: resolver config del tenant (producción/integración)
        try:
            config = CompanyInvoiceConfig.objects.get(
                organization=order.organization
            )
        except CompanyInvoiceConfig.DoesNotExist:
            # Config faltante: marcar como fallida, no romper flujo
            order.invoice_status = 'failed'
            order.save()
            return {
                'status': 'failed',
                'error': 'CompanyInvoiceConfig not found',
                'external_id': None
            }

        # Obtener provider (Mock o Real según enabled)
        self.provider = get_invoice_provider(config)

        # Ejecutar creación de factura
        result = self.provider.create_invoice(order)

        # Persistir resultado en order
        order.invoice_status = result['status']
        order.invoice_external_id = result.get('external_id')
        order.save()

        return result

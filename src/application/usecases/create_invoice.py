from src.domain.models import CompanyInvoiceConfig
from src.domain.exceptions import NubefactPermanentError
from src.application.providers.factory import get_invoice_provider


class CreateInvoiceUseCase:

    def __init__(self, provider=None):
        self.provider = provider

    def execute(self, order):
        # Idempotencia: factura ya emitida — no duplicar
        if order.invoice_external_id:
            return {
                'status': order.invoice_status,
                'external_id': order.invoice_external_id,
                'error': None,
            }

        # Provider inyectado: path de testing
        if self.provider is not None:
            result = self.provider.create_invoice(order)
            if hasattr(order, 'save') and callable(order.save):
                order.invoice_status = result['status']
                order.invoice_external_id = result.get('external_id')
                order.save()
            return result

        # Resolver config del tenant
        try:
            config = CompanyInvoiceConfig.objects.get(organization=order.organization)
        except CompanyInvoiceConfig.DoesNotExist:
            # Config faltante es un error permanente — no tiene sentido reintentar
            raise NubefactPermanentError('CompanyInvoiceConfig not found')

        provider = get_invoice_provider(config)

        # Excepciones del provider (NubefactTemporaryError / NubefactPermanentError)
        # se propagan al caller (create_invoice_task) para manejo diferenciado.
        result = provider.create_invoice(order)

        order.invoice_status = result['status']
        order.invoice_external_id = result.get('external_id')
        order.save()

        return result

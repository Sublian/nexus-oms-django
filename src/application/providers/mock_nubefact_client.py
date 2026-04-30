# MockNubefactClient para desarrollo sin credenciales reales
# Emula respuestas de Nubefact sin hacer llamadas HTTP reales

import uuid
from .invoice_provider import InvoiceProvider


class MockNubefactClient(InvoiceProvider):
    # Simula respuestas de Nubefact para testing y desarrollo

    def create_invoice(self, order):
        # Generar ID externo simulado
        external_id = f"MOCK-{str(uuid.uuid4())[:8].upper()}"

        # Simular éxito
        return {
            'status': 'issued',
            'external_id': external_id,
            'error': None,
            'organization': order.organization.id,
            'order_id': order.id,
        }

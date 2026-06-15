import uuid
from src.domain.exceptions import NubefactTemporaryError
from .invoice_provider import InvoiceProvider


class MockNubefactClient(InvoiceProvider):
    """
    Cliente fake para desarrollo y tests.

    Configurar escenario por instancia antes de llamar get_invoice_status:
        client = MockNubefactClient(config)
        client.status_scenario = 'rejected'   # default: 'accepted'

    Escenarios disponibles: accepted | observed | rejected | pending | timeout | error
    """

    status_scenario: str = 'accepted'

    def create_invoice(self, order) -> dict:
        external_id = f"MOCK-{str(uuid.uuid4())[:8].upper()}"
        return {
            'status': 'submitted',
            'external_id': external_id,
            'hash': f"MOCK-HASH-{external_id}",
            'error': None,
            'organization': order.organization.id,
            'order_id': order.id,
        }

    def get_invoice_status(self, order, external_id: str) -> dict:
        scenario = self.status_scenario

        if scenario == 'timeout':
            raise NubefactTemporaryError(f"Mock timeout — external_id={external_id}")

        if scenario == 'error':
            raise NubefactTemporaryError(f"Mock network error — external_id={external_id}")

        accepted   = scenario == 'accepted'
        observed   = scenario == 'observed'
        rejected   = scenario == 'rejected'
        # 'pending' -> los tres False, sigue en procesamiento SUNAT

        return {
            'accepted':           accepted,
            'observed':           observed,
            'rejected':           rejected,
            'hash':               f"MOCK-HASH-{external_id}" if (accepted or observed) else None,
            'provider_reference': f"MOCK-REF-{external_id}",
            'raw_response':       {'mock': True, 'scenario': scenario, 'external_id': external_id},
        }

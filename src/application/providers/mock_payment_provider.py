import uuid

from src.domain.models import Payment

from .payment_provider import PaymentProvider


class MockPaymentProvider(PaymentProvider):
    """
    Pasarela fake para desarrollo y tests — espejo de MockNubefactClient.

    Reglas determinísticas por método (si status_scenario es None):
      CASH     → approved inmediato
      CARD     → approved, salvo que la referencia empiece con 'REJECT'
      TRANSFER → pending (se aprueba al consultar get_payment_status)
      WALLET   → pending (se aprueba al consultar get_payment_status)

    Forzar un escenario global asignando status_scenario por instancia:
      provider = MockPaymentProvider(config)
      provider.status_scenario = 'declined'   # approved | pending | declined
    """

    status_scenario = None

    def process_payment(self, payment) -> dict:
        external_id = f"PAY-MOCK-{str(uuid.uuid4())[:8].upper()}"

        forced = self.status_scenario
        if forced in ('approved', 'pending', 'declined'):
            return self._response(forced, external_id,
                                  error=None if forced != 'declined' else 'Mock: transacción rechazada')

        if payment.method == Payment.PaymentMethod.CASH:
            return self._response('approved', external_id)

        if payment.method == Payment.PaymentMethod.CREDIT_CARD:
            ref = (payment.transaction_reference or '').upper()
            if ref.startswith('REJECT'):
                return self._response('declined', external_id,
                                      error='Tarjeta rechazada por el emisor')
            return self._response('approved', external_id)

        # TRANSFER / WALLET → confirmación asíncrona
        return self._response('pending', external_id)

    def get_payment_status(self, payment) -> dict:
        # El mock siempre termina aprobando los pendientes en la 1ra consulta.
        # Con un proveedor real aquí iría la llamada HTTP de estado.
        forced = self.status_scenario
        if forced == 'declined':
            return self._response('declined', payment.external_reference,
                                  error='Mock: transacción rechazada')
        if forced == 'pending':
            return self._response('pending', payment.external_reference)
        return self._response('approved', payment.external_reference)

    def _response(self, status, external_id, error=None):
        return {
            'status': status,
            'external_id': external_id,
            'error': error,
            'raw_response': {
                'mock': True,
                'provider': 'mock',
                'status': status,
                'external_id': external_id,
            },
        }

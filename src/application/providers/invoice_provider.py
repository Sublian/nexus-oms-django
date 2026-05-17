from abc import ABC, abstractmethod


class InvoiceProvider(ABC):
    """
    Contrato para proveedores de facturación electronica.

    Contrato de excepciones:
      - NubefactTemporaryError: timeout, 502, 503 — el caller puede reintentar
      - NubefactPermanentError: 400, auth error, payload invalido — no reintentar
      - Exito: retorna dict {'status': 'issued', 'external_id': str, 'error': None}
    """

    def __init__(self, config):
        self.config = config

    @abstractmethod
    def create_invoice(self, order) -> dict:
        pass

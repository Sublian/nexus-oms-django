from abc import ABC, abstractmethod


class InvoiceProvider(ABC):
    """
    Contrato para proveedores de facturacion electronica.

    Excepciones que pueden lanzar ambos metodos:
      NubefactTemporaryError — timeout, 5xx: el caller puede reintentar
      NubefactPermanentError — 4xx, auth, payload invalido: no reintentar

    Contrato de retorno de create_invoice:
      {'status': 'submitted', 'external_id': str, 'hash': str | None, 'error': None}

    Contrato de retorno de get_invoice_status:
      {
          'accepted':           bool,        # SUNAT confirmo el comprobante
          'observed':           bool,        # SUNAT acepto con observaciones
          'rejected':           bool,        # SUNAT rechazo el comprobante
          'hash':               str | None,  # Hash CDR — prueba de recepcion Nubefact
          'provider_reference': str | None,  # Referencia interna de Nubefact
          'raw_response':       dict,        # Respuesta completa para auditoria
      }
      Invariante: a lo sumo uno de (accepted, observed, rejected) es True.
      Si los tres son False, el comprobante sigue en procesamiento SUNAT.
    """

    def __init__(self, config):
        self.config = config

    @abstractmethod
    def create_invoice(self, order) -> dict:
        pass

    @abstractmethod
    def get_invoice_status(self, order, external_id: str) -> dict:
        pass

from abc import ABC, abstractmethod


class PaymentProvider(ABC):
    """
    Contrato para pasarelas de pago.

    Excepciones que pueden lanzar ambos metodos:
      PaymentGatewayTemporaryError — timeout, 5xx: el caller puede reintentar
      PaymentGatewayPermanentError — 4xx, auth, payload invalido: no reintentar

    Contrato de retorno de process_payment:
      {
          'status':        'approved' | 'pending' | 'declined',
          'external_id':   str,          # id de transaccion en la pasarela
          'error':         str | None,   # motivo cuando declined
          'raw_response':  dict,         # respuesta completa para auditoria
      }

    Contrato de retorno de get_payment_status:
      Mismo contrato que process_payment (consulta de un pago ya enviado).
      'external_id' puede venir null — el payment ya lo guarda.

    Semantica de estados:
      approved — la pasarela confirmo el cobro → la orden puede pasar a PAID
      pending  — en espera (transferencia / Yape-Plin / 3DS) → consultar luego
      declined — rechazado por la pasarela o el emisor → no reintentar igual
    """

    def __init__(self, config):
        self.config = config

    @abstractmethod
    def process_payment(self, payment) -> dict:
        """Envia un cobro nuevo a la pasarela."""
        pass

    @abstractmethod
    def get_payment_status(self, payment) -> dict:
        """Consulta el estado de una transaccion ya enviada."""
        pass

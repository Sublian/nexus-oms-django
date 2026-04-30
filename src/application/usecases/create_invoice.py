# UseCase: Crear factura desde orden pagada.
# Separa intención (workflow) de implementación (Nubefact).
# Fase 2: Nubefact client se inyecta aquí, sin acoplamiento directo al workflow.


class CreateInvoiceUseCase:
    # Placeholder para Fase 2. Nubefact se conecta aquí sin romper workflow.

    def __init__(self, nubefact_client=None):
        # nubefact_client: inyectable para testing
        self.nubefact_client = nubefact_client

    def execute(self, order):
        # Fase 1: placeholder. Fase 2: self.nubefact_client.create_invoice(order)
        if self.nubefact_client:
            return self.nubefact_client.create_invoice(order)
        return None

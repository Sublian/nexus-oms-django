from src.domain.exceptions import NubefactPermanentError
from src.domain.models.config import CompanyInvoiceConfig
from src.application.providers.factory import get_invoice_provider


class InvoiceStatusQueryUseCase:
    """
    Consulta el estado de un comprobante en Nubefact/SUNAT y actualiza Order.

    Recibe una entrada de InvoiceSyncQueue, delega la consulta HTTP al provider
    y actualiza invoice_status + invoice_hash del Order segun el resultado.

    Retorna el dict normalizado del provider para que el task pueda actualizar
    la cola (InvoiceSyncQueue) sin tener que re-interpretar el resultado.

    Separacion de responsabilidades:
      - Task:    orquesta, maneja reintentos, actualiza InvoiceSyncQueue
      - UseCase: logica de negocio, interpreta resultado, actualiza Order
      - Provider: contrato ABC — abstrae Nubefact vs Mock
      - HTTP Client: unica pieza que toca requests
    """

    def __init__(self, provider=None):
        self._provider = provider  # inyeccion para tests; None = resolucion dinamica

    def execute(self, sync_entry) -> dict:
        order = sync_entry.order

        if not order.invoice_external_id:
            raise NubefactPermanentError(
                f"order_id={order.id} no tiene invoice_external_id — no se puede consultar"
            )

        if self._provider is not None:
            provider = self._provider
        else:
            try:
                config = CompanyInvoiceConfig.objects.get(organization=order.organization)
            except CompanyInvoiceConfig.DoesNotExist:
                raise NubefactPermanentError(
                    f"CompanyInvoiceConfig no encontrada para org={order.organization_id}"
                )
            provider = get_invoice_provider(config)


        result = provider.get_invoice_status(order.invoice_external_id)

        # Actualizar invoice_status en Order segun resultado normalizado del provider
        new_status = self._resolve_status(result)
        update_fields = ['invoice_status']

        if new_status != order.invoice_status:
            order.invoice_status = new_status

        # Persistir hash cuando llega por primera vez
        if result.get('hash') and not order.invoice_hash:
            order.invoice_hash = result['hash']
            update_fields.append('invoice_hash')

        order.save(update_fields=update_fields)

        return result

    # ── helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _resolve_status(result: dict) -> str:
        """Traduce el resultado del provider al invoice_status de negocio."""
        if result.get('rejected'):
            return 'rejected'
        if result.get('observed'):
            return 'observed'
        if result.get('accepted'):
            return 'accepted'
        # Ninguno de los flags terminales — SUNAT sigue procesando
        return 'sync_pending'

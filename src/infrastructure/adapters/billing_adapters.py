from abc import ABC, abstractmethod
from decimal import Decimal
import logging

# Configuración del registrador de eventos del sistema
logger = logging.getLogger(__name__)

class InvoiceAdapterInterface(ABC):
    """
    Interfaz abstracta que define el contrato para los adaptadores de facturación.
    Cualquier proveedor futuro (ej. Nubefact, Sunat Directo, etc.) debe heredar
    de esta clase e implementar sus métodos obligatorios.
    """
    
    @abstractmethod
    def send_invoice(self, order_data: dict) -> dict:
        """
        Envía los datos del pedido al proveedor de facturación electrónica.
        
        Args:
            order_data (dict): Diccionario con los datos consolidados del pedido.
            
        Returns:
            dict: Respuesta estandarizada del proveedor (ID de factura, estado, URL).
        """
        pass


class NubefactMockAdapter(InvoiceAdapterInterface):
    """
    Adaptador simulado (Mock) para Nubefact. Cumple con el contrato de la interfaz
    y permite avanzar con el desarrollo del MVP sin depender de conexiones API reales.
    """
    
    def send_invoice(self, order_data: dict) -> dict:
        """
        Simula el procesamiento y envío de la factura electrónica a Nubefact.
        """
        logger.info(f"[MOCK NUBEFACT] Iniciando envío de comprobante para la orden: {order_data.get('order_id')}")
        
        # Extracción de variables financieras simulando el payload de Nubefact
        order_id = order_data.get("order_id")
        total = order_data.get("total_amount", Decimal("0.00"))
        tenant_id = order_data.get("organization_id")
        
        # Simulación de respuesta exitosa del proveedor externo
        mock_response = {
            "status": "SUCCESS",
            "invoice_number": f"FFF1-{order_id:05d}",
            "external_id": f"nube-{tenant_id}-{order_id}",
            "pdf_url": f"https://api.nubefact.mock/v1/pdf/{order_id}",
            "total_processed": float(total)
        }
        
        logger.info(f"[MOCK NUBEFACT] Factura generada con éxito: {mock_response['invoice_number']}")
        return mock_response
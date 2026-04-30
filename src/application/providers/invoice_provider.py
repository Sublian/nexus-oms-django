# Interfaz abstracta para proveedores de facturación
# Implementaciones concretas: MockNubefactClient, NubefactClient (Fase 2.5)

from abc import ABC, abstractmethod


class InvoiceProvider(ABC):
    # Contrato que todo proveedor debe cumplir

    def __init__(self, config):
        # config: CompanyInvoiceConfig (tenant-aware)
        self.config = config

    @abstractmethod
    def create_invoice(self, order):
        # Crear factura. Retorna dict con:
        # {
        #   'status': 'issued' | 'failed',
        #   'external_id': 'MOCK-xxx' | 'NFE-xxx',
        #   'error': None | 'error message'
        # }
        pass

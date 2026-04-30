# Factory para resolver el provider dinámico por tenant
# Punto crítico: evitar contaminación entre tenants

from .mock_nubefact_client import MockNubefactClient


def get_invoice_provider(config):
    # config: CompanyInvoiceConfig (tenant-aware)
    # Si enabled=False, siempre Mock (desarrollo)
    # Si enabled=True e implementamos NubefactClient en Fase 2.5, usaremos ese

    if not config.enabled:
        return MockNubefactClient(config)

    # Fase 2.5: Aquí iría NubefactClient real
    # from .nubefact_client import NubefactClient
    # return NubefactClient(config)

    # Por ahora, usar Mock incluso con enabled=True hasta tener NubefactClient
    return MockNubefactClient(config)

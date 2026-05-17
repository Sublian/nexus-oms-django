from .mock_nubefact_client import MockNubefactClient


def get_invoice_provider(config):
    """
    Resuelve el provider de facturacion para un tenant dado su config.

    provider_type='nubefact' -> NubefactClient (HTTP real, produccion)
    provider_type='mock'     -> MockNubefactClient (sin HTTP, desarrollo/tests)
    """
    if config.provider_type == 'nubefact':
        from .nubefact_client import NubefactClient
        return NubefactClient(config)

    return MockNubefactClient(config)

from .mock_nubefact_client import MockNubefactClient
from .mock_payment_provider import MockPaymentProvider


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


def get_payment_provider(config):
    """
    Resuelve el provider de pagos para un tenant dado su PaymentFeeConfig.

    provider_type='izipay' -> IzipayPaymentProvider (HTTP real — futuro)
    cualquier otro valor   -> MockPaymentProvider (sin HTTP, desarrollo/tests)
    """
    if getattr(config, 'provider_type', 'mock') == 'izipay':
        raise NotImplementedError(
            "IzipayPaymentProvider aún no está implementado (Fase A usa el mock)."
        )

    return MockPaymentProvider(config)

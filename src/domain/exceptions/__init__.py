class NubefactTemporaryError(Exception):
    """Timeout, 502, 503 — retry is safe."""
    pass


class NubefactPermanentError(Exception):
    """400, auth error, invalid payload — do not retry."""
    pass


class PaymentGatewayTemporaryError(Exception):
    """Timeout, 5xx de la pasarela — reintentar es seguro."""
    pass


class PaymentGatewayPermanentError(Exception):
    """4xx, auth, payload inválido — no reintentar."""
    pass

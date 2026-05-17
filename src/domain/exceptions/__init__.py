class NubefactTemporaryError(Exception):
    """Timeout, 502, 503 — retry is safe."""
    pass


class NubefactPermanentError(Exception):
    """400, auth error, invalid payload — do not retry."""
    pass

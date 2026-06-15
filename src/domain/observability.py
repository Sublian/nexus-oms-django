"""
Taxonomía de errores para observabilidad de llamadas HTTP externas.

Clasificación dinámica de excepciones y códigos de estado HTTP
en categorías que determinan estrategia de reintento y escalación.
"""
from enum import Enum


class ErrorCategory(str, Enum):
    """Categorías de error para logging y análisis de patrones."""
    TEMPORARY = "TEMPORARY"      # Timeout, 502, 503 — reintentable
    PERMANENT = "PERMANENT"      # 400, 401, 403, 422 — no reintentar
    AUTH = "AUTH"                # 401, 403 — error de autenticación
    VALIDATION = "VALIDATION"    # 422 — payload inválido
    RATE_LIMIT = "RATE_LIMIT"   # 429 — throttling del proveedor


def classify_error(exception_or_status_code) -> ErrorCategory:
    """
    Clasifica dinámicamente una excepción o código HTTP en una categoría.

    Args:
        exception_or_status_code: Exception object o int (HTTP status code)

    Returns:
        ErrorCategory enum value
    """
    # Si es un código HTTP (int)
    if isinstance(exception_or_status_code, int):
        status_code = exception_or_status_code

        if status_code == 429:
            return ErrorCategory.RATE_LIMIT
        elif status_code in (401, 403):
            return ErrorCategory.AUTH
        elif status_code == 422:
            return ErrorCategory.VALIDATION
        elif status_code in (400, 404, 405, 409, 410, 411, 413, 415, 451):
            return ErrorCategory.PERMANENT
        elif status_code in (500, 502, 503, 504, 505, 506, 507, 508, 510, 511):
            return ErrorCategory.TEMPORARY
        else:
            # Códigos 2xx, 3xx → éxito (no debería llegar aquí)
            # Otros 4xx → permanente
            # Otros 5xx → temporal
            return ErrorCategory.PERMANENT if status_code < 500 else ErrorCategory.TEMPORARY

    # Si es una excepción
    exception_name = type(exception_or_status_code).__name__

    if 'Timeout' in exception_name or 'ConnectionError' in exception_name:
        return ErrorCategory.TEMPORARY
    elif 'Auth' in exception_name:
        return ErrorCategory.AUTH
    elif 'Validation' in exception_name:
        return ErrorCategory.VALIDATION
    elif 'RateLimit' in exception_name:
        return ErrorCategory.RATE_LIMIT
    elif 'Temporary' in exception_name:
        return ErrorCategory.TEMPORARY
    elif 'Permanent' in exception_name:
        return ErrorCategory.PERMANENT

    # Default: si no se puede clasificar, asumir permanente para seguridad
    return ErrorCategory.PERMANENT

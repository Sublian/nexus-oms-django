from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache


@never_cache
def liveness(request):
    """¿Está el proceso vivo? No toca nada externo: siempre 200."""
    return JsonResponse({"status": "ok"})


@never_cache
def readiness(request):
    """¿Está listo para recibir tráfico? Comprueba dependencias críticas."""
    checks = {}
    ok = True

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"
        ok = False

    try:
        cache.get("__nexus_readiness__")
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"
        ok = False

    status = 200 if ok else 503
    payload = {"status": "ok" if ok else "error", "checks": checks}
    return JsonResponse(payload, status=status)

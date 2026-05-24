"""
Metadatos de presentación para Order.invoice_status.

Fuente única de verdad para label, color, severidad y comportamiento visual.
Importar desde cualquier capa: admin, serializers, templates (vía invoice_tags).
"""

INVOICE_STATUS_UI = {
    'pending': {
        'label':      'Pendiente',
        'badge':      'bg-gray-100 text-gray-500',
        'severity':   'info',
        'terminal':   False,
        'success':    False,
    },
    'queued': {
        'label':      'En Cola',
        'badge':      'bg-blue-50 text-blue-600',
        'severity':   'info',
        'terminal':   False,
        'success':    False,
    },
    'processing': {
        'label':      'Procesando',
        'badge':      'bg-blue-100 text-blue-700',
        'severity':   'info',
        'terminal':   False,
        'success':    False,
    },
    'submitted': {
        'label':      'Enviada',
        'badge':      'bg-sky-100 text-sky-700',
        'severity':   'info',
        'terminal':   False,
        'success':    False,
    },
    'sync_pending': {
        'label':      'Verificando SUNAT',
        'badge':      'bg-yellow-100 text-yellow-700',
        'severity':   'warning',
        'terminal':   False,
        'success':    False,
    },
    'sync_processing': {
        'label':      'Consultando SUNAT',
        'badge':      'bg-indigo-100 text-indigo-700',
        'severity':   'info',
        'terminal':   False,
        'success':    False,
    },
    'accepted': {
        'label':      'Aceptada SUNAT',
        'badge':      'bg-emerald-100 text-emerald-700',
        'severity':   'success',
        'terminal':   True,
        'success':    True,
    },
    'observed': {
        'label':      'Observada SUNAT',
        'badge':      'bg-amber-100 text-amber-700',
        'severity':   'warning',
        'terminal':   True,
        'success':    True,
    },
    'rejected': {
        'label':      'Rechazada SUNAT',
        'badge':      'bg-red-100 text-red-700',
        'severity':   'error',
        'terminal':   True,
        'success':    False,
    },
    'retrying': {
        'label':      'Reintentando',
        'badge':      'bg-orange-100 text-orange-700',
        'severity':   'warning',
        'terminal':   False,
        'success':    False,
    },
    'failed': {
        'label':      'Fallida',
        'badge':      'bg-red-100 text-red-800',
        'severity':   'error',
        'terminal':   True,
        'success':    False,
    },
    'cancelled': {
        'label':      'Cancelada',
        'badge':      'bg-gray-100 text-gray-500',
        'severity':   'info',
        'terminal':   True,
        'success':    False,
    },
    'dead_letter': {
        'label':      'Sin Respuesta',
        'badge':      'bg-rose-100 text-rose-700',
        'severity':   'error',
        'terminal':   True,
        'success':    False,
    },
    'exhausted': {
        'label':      'Reintentos Agotados',
        'badge':      'bg-red-100 text-red-900',
        'severity':   'error',
        'terminal':   True,
        'success':    False,
    },
}

_FALLBACK = {
    'label':    'Desconocido',
    'badge':    'bg-gray-100 text-gray-400',
    'severity': 'info',
    'terminal': False,
    'success':  False,
}


def get_invoice_status_ui(status: str) -> dict:
    return INVOICE_STATUS_UI.get(status, _FALLBACK)

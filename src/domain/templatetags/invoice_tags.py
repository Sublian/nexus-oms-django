from django import template
from src.domain.invoice_status_ui import get_invoice_status_ui

register = template.Library()


@register.filter
def invoice_ui(status):
    """
    Retorna el dict de metadatos de presentación para un invoice_status dado.

    Uso en template:
        {% load invoice_tags %}
        {% with ui=order.invoice_status|invoice_ui %}
            <span class="{{ ui.badge }}">{{ ui.label }}</span>
        {% endwith %}
    """
    return get_invoice_status_ui(status)

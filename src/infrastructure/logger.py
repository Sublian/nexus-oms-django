import logging

# Logger dedicado al flujo de órdenes. Configurado en settings.LOGGING["order_workflow"].
# Salida por consola en dev; en prod apuntar a un handler de archivo o servicio externo.
logger = logging.getLogger("order_workflow")

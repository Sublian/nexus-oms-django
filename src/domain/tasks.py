from celery import shared_task
import time

@shared_task
def process_order_notifications(order_id):
    """
    Tarea asíncrona para procesar notificaciones post-venta.
    """
    print(f"📧 Iniciando proceso de notificación para el Pedido #{order_id}...")
    
    # Simulamos un proceso pesado (ej: conectar con un servidor de correos)
    time.sleep(5) 
    
    print(f"✅ Notificación enviada exitosamente para el Pedido #{order_id}")
    return True
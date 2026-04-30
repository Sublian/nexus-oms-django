# Estados de la orden — fuente única de verdad.
# Usar solo constantes. Nunca strings sueltos en vistas/servicios.
class OrderStatus:
    DRAFT = 'DRAFT'
    PENDING = 'PENDING'
    COURTESY = 'COURTESY'
    PAID = 'PAID'
    SHIPPED = 'SHIPPED'
    DELIVERED = 'DELIVERED'
    COMPLETED = 'COMPLETED'
    RETURNED = 'RETURNED'
    CANCELLED = 'CANCELLED'

    CHOICES = [
        (DRAFT, 'Borrador'),
        (PENDING, 'Pendiente'),
        (COURTESY, 'Cortesía'),
        (PAID, 'Pagado'),
        (SHIPPED, 'Enviado'),
        (DELIVERED, 'Entregado'),
        (COMPLETED, 'Completado'),
        (RETURNED, 'Retornado'),
        (CANCELLED, 'Cancelado'),
    ]

    VALID_TRANSITIONS = {
        DRAFT: [PENDING, COURTESY, CANCELLED],
        PENDING: [PAID, CANCELLED],
        COURTESY: [SHIPPED, DELIVERED, CANCELLED],
        PAID: [SHIPPED, CANCELLED],
        SHIPPED: [DELIVERED, CANCELLED],
        DELIVERED: [COMPLETED, RETURNED],
    }

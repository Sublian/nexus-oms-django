from abc import ABC, abstractmethod

class NotificationStrategy(ABC):
    @abstractmethod
    def send(self, user_contact, message, context=None):
        """
        user_contact: email, phone number, or telegram_id
        message: el texto o cuerpo de la notificación
        context: dict con datos extra (ej: link al reporte)
        """
        pass

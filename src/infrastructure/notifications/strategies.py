from src.domain.notifications.base import NotificationStrategy
from django.core.mail import send_mail
import requests

class EmailNotification(NotificationStrategy):
    def send(self, user_email, message, context=None):
        # Lógica de Django Mail
        send_mail(
            subject=context.get('subject', 'Notificación Nexus'),
            message=message,
            from_email=None,
            recipient_list=[user_email],
        )
        print(f"📧 Email enviado a {user_email}")

class TelegramNotification(NotificationStrategy):
    def send(self, user_email, message, context=None):
        # Aquí iría la llamada al bot de Telegram
        # token = settings.TELEGRAM_BOT_TOKEN
        print(f"🤖 Telegram enviado: {message[:20]}...")

class WhatsAppNotification(NotificationStrategy):
    def send(self, user_email, message, context=None):
        # Aquí iría la integración con Twilio o Meta API
        print(f"🟢 WhatsApp enviado: {message[:20]}...")
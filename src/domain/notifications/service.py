from src.infrastructure.notifications.strategies import (
    EmailNotification, TelegramNotification, WhatsAppNotification
)

class NotificationService:
    @staticmethod
    def notify_report_ready(organization_config, user_email, report_name):
        strategies = []
        
        # Siempre email como principal (según tu requerimiento)
        strategies.append(EmailNotification())
        
        # Cargar secundarias según configuración del Tenant
        if organization_config.get('telegram_enabled'):
            strategies.append(TelegramNotification())
        if organization_config.get('whatsapp_enabled'):
            strategies.append(WhatsAppNotification())
            
        message = f"Hola, tu reporte '{report_name}' ya está disponible para descargar."
        
        for strategy in strategies:
            strategy.send(user_email, message, context={'subject': 'Reporte Listo'})